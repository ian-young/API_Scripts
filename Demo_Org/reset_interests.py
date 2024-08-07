"""
Author: Ian Young
Purpose: An interactive file to clean a Verkada Command organization.
Compare plates to a pre-defined array of names.
These names will be "persistent plates/persons" which are to remain in
Command. Any person or plate not marked thusly will be deleted from the org.
"""

# Import essential libraries
import logging
import threading
import time
from os import getenv

import datetime
import requests
from dotenv import load_dotenv

import QoL.custom_exceptions as custom_exceptions

load_dotenv()  # Load credentials file

ORG_ID = getenv("")
API_KEY = getenv("")

# This will help prevent exceeding the call limit
CALL_COUNT = 0
CALL_COUNT_LOCK = threading.Lock()

# Set timeout for a 429
MAX_RETRIES = 10
DEFAULT_RETRY_DELAY = 0.25
BACKOFF = 0.25

# Set logger
log = logging.getLogger()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Set the full name for which plates are to be persistent
PERSISTENT_PLATES = [""]
PERSISTENT_PERSONS = [""]

# Set API endpoint URLs
PLATE_URL = "https://api.verkada.com/cameras/v1/\
analytics/lpr/license_plate_of_interest"
PERSON_URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"


##############################################################################
###################################  Misc  ###################################
##############################################################################


class RateLimiter:
    """
    The purpose of this class is to limit how fast multi-threaded actions are
    created to prevent hitting the API limit.
    """

    def __init__(self, rate_limit, max_events_per_sec=10, pacing=1):
        """
        Initialization of the rate limiter.

        :param rate_limit: The value of how many threads may be made each sec.
        :type rate_limit: int
        :param max_events_per_sec: Maximum events allowed per second.
        :type: int, optional
        :param pacing: Sets the interval of the clock in seconds.
        :type pacing: int, optional
        :return: None
        :rtype: None
        """
        self.rate_limit = rate_limit
        self.lock = threading.Lock()  # Local lock to prevent race conditions
        self.max_events_per_sec = max_events_per_sec
        self.pacing = pacing
        self.start_time = 0
        self.event_count = 0

    def acquire(self):
        """
        States whether or not the program may create new threads or not.

        :return: Boolean value stating whether new threads may be made or not.
        :rtype: bool
        """
        with self.lock:
            current_time = time.time()  # Define current time

            if not hasattr(self, "start_time"):
                # Check if attribute 'start_time' exists, if not, make it.
                self.start_time = current_time
                self.event_count = self.pacing
                return True

            # How much time has passed since starting
            elapsed_since_start = current_time - self.start_time

            # Check if it's been less than 1sec and less than 10 events have
            # been made.
            if (
                elapsed_since_start < self.pacing / self.rate_limit
                and self.event_count < self.max_events_per_sec
            ):
                self.event_count += 1
            elif elapsed_since_start >= self.pacing / self.rate_limit:
                self.start_time = current_time
                self.event_count = 2
            else:
                # Calculate the time left before next wave
                remaining_time = self.pacing - (current_time - self.start_time)
                time.sleep(remaining_time)  # Wait before next wave

            return True


def run_thread_with_rate_limit(threads, rate_limit=10):
    """
    Run a thread with rate limiting.

    :param target: The target function to be executed in the thread:
    :type targe: function:
    :return: The thread that was created and ran
    :rtype: thread
    """
    limiter = RateLimiter(rate_limit=rate_limit)

    def run_thread(thread):
        limiter.acquire()
        log.debug(
            "Starting thread %s at time %s",
            thread.name,
            datetime.datetime.now().strftime("%H:%M:%S"),
        )
        thread.start()

    for thread in threads:
        run_thread(thread)

    for thread in threads:
        thread.join()


def warn():
    """Prints a warning message before continuing"""
    print("-------------------------------")
    print("WARNING!!!")
    print("Please make sure you have changed the persistent plates variable.")
    print("Otherwise all of your plates will be deleted.")
    print("Please double-check spelling, as well!")
    print("-------------------------------")
    cont = None

    while cont not in ["", " "]:
        cont = str(input("Press enter to continue\n")).strip()


def clean_list(messy_list):
    """
    Removes any None values from error codes.

    :param messy_list: The list with potential None values to clean.
    :type messy_list: list
    :return: A list with no None values
    :rtype: list
    """
    return [value for value in messy_list if value is not None]


##############################################################################
#  All things people  #
##############################################################################


def check_people(safe, to_delete, persons):
    """
    Checks with the user before continuing with the purge.

    :param safe: A list of people that are marked as safe.
    :type safe: list
    :param to_delete: A list of people to delete during the purge.
    :type to_delete: list
    :param persons: A list of all people found in the organization.
    :type persons: list
    """
    trust_level = None  # Pre-define
    ok = None  # Pre-define

    while trust_level not in ["1", "2", "3"]:
        print(
            "1. Check marked persistent persons against what the \
application found."
        )
        print("2. Check what is marked for deletion by the application.")
        print("3. Trust the process and blindly move forward.")

        trust_level = str(input("- ")).strip()

        if trust_level == "1":
            print("-------------------------------")
            print("Please check that the two lists match: ")

            safe_names = [
                print_person_name(person_id, persons) for person_id in safe
            ]

            print(", ".join(safe_names))
            print("vs")
            print(", ".join(PERSISTENT_PERSONS))
            print("-------------------------------")

            while ok not in ["y", "n"]:
                ok = str(input("Do they match?(y/n) ")).strip().lower()

                if ok == "y":
                    purge_people(to_delete, persons)

                elif ok == "n":
                    print("Please check the input values")
                    print("Exiting...")

                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

        elif trust_level == "2":
            print("-------------------------------")
            print("Here are the persons being purged: ")

            delete_names = [
                print_person_name(person_id, persons)
                for person_id in to_delete
            ]
            print(", ".join(delete_names))
            print("-------------------------------")

            while ok not in ["y", "n"]:
                ok = str(input("Is this list accurate?(y/n) ")).strip().lower()

                if ok == "y":
                    purge_people(to_delete, persons)

                elif ok == "n":
                    print("Please check the input values.")
                    print("Exiting...")

                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

        elif trust_level == "3":
            print("Good luck!")
            purge_people(to_delete, persons)

        else:
            print("Invalid input. Please enter '1', '2', or '3'.")


def get_people(org_id=ORG_ID, api_key=API_KEY):
    """
    Returns JSON-formatted persons in a Command org.

    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: A List of dictionaries of people in an organization.
    :rtype: list
    """
    headers = {"accept": "application/json", "x-api-key": api_key}

    params = {
        "org_id": org_id,
    }

    response = requests.get(
        PERSON_URL, headers=headers, params=params, timeout=5
    )

    if response.status_code == 200:
        data = response.json()  # Parse the response

        # Extract as a list
        persons = data.get("persons_of_interest")

        try:
            iter(persons)
        except (TypeError, AttributeError):
            log.error("People are not iterable.")
            return

        return persons
    else:
        log.critical(
            "Person - Error with retrieving persons. Status code %s",
            {response.status_code},
        )
        return None


def get_people_ids(persons=None):
    """
    Returns an array of all PoI labels in an organization.

    :param persons: A list of dictionaries representing PoIs in an
    organization. Each dictionary should have 'person_id' key.
    Defaults to None.
    :type persons: list, optional
    :return: A list of IDs of the PoIs in an organization.
    :rtype: list
    """
    person_id = []

    for person in persons:
        if person.get("person_id"):
            person_id.append(person.get("person_id"))
        else:
            log.error(
                "There has been an error with person %s.", person.get("label")
            )
    return person_id


def get_person_id(person, persons=None):
    """
    Returns the Verkada ID for a given PoI.

    :param person: The label of a PoI whose ID is being searched for.
    :type person: str
    :param persons: A list of PoI IDs found inside of an organization.
    Each dictionary should have the 'person_id' key. Defaults to None.
    :type persons: list, optional
    :return: The person ID of the given PoI.
    :rtype: str
    """
    if person_id := next(
        (name["person_id"] for name in persons if name["label"] == person),
        None,
    ):
        return person_id
    log.warning("Person %s was not found in the database...", person)
    return None


def delete_person(person, persons, org_id=ORG_ID, api_key=API_KEY):
    """
    Deletes the given person from the organization.

    :param person: The person to be deleted.
    :type person: str
    :param persons: A list of PoI IDs found inside of an organization.
    :type persons: list
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: None
    :rtype: None
    """
    local_data = threading.local()
    local_data.RETRY_DELAY = DEFAULT_RETRY_DELAY

    headers = {"accept": "application/json", "x-api-key": api_key}

    log.info("Running for person: %s", print_person_name(person, persons))

    params = {"org_id": org_id, "person_id": person}

    try:
        for _ in range(MAX_RETRIES):
            response = requests.delete(
                PERSON_URL, headers=headers, params=params, timeout=5
            )

            if response.status_code == 429:
                log.info(
                    "%s response: 429. Retrying in %ss.",
                    print_person_name(person, persons),
                    local_data.RETRY_DELAY,
                )

                time.sleep(local_data.RETRY_DELAY)

                local_data.RETRY_DELAY += BACKOFF

            else:
                break

        if response.status_code == 429:
            raise custom_exceptions.APIThrottleException("API throttled")

    # Handle exceptions
    except custom_exceptions.APIThrottleException:
        log.critical(
            "Person - Hit API request rate limit of 500 requests per minute."
        )

    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Person -"
        ) from e


def purge_people(delete, persons, org_id=ORG_ID, api_key=API_KEY):
    """
    Purges all PoIs that aren't marked as safe/persistent.

    :param delete: A list of PoIs to be deleted from the organization.
    :type delete: list
    :param persons: A list of PoIs found inside of an organization.
    :type persons: list
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: Returns the value of 1 if completed successfully.
    :rtype: int
    """
    if not delete:
        log.warning("Person - There's nothing here")
        return

    log.info("Person - Purging...")

    person_start_time = time.time()
    threads = []
    for person in delete:
        # Toss delete function into a new thread
        thread = threading.Thread(
            target=delete_person,
            args=(
                person,
                persons,
                org_id,
                api_key,
            ),
        )
        threads.append(thread)  # Add the thread to the pile

    run_thread_with_rate_limit(threads)

    person_end_time = time.time()
    person_elapsed_time = person_end_time - person_start_time

    log.info("Person - Purge complete.")
    log.info("Person - Time to complete: %.2f", person_elapsed_time)

    return 1  # Completed


def print_person_name(to_delete, persons):
    """
    Returns the label of a PoI with a given ID

    :param to_delete: The person ID whose name is being searched for in the
    dictionary.
    :type to_delete: str
    :param persons: A list of PoIs found inside of an organization.
    :type persons: list
    :return: Returns the name of the person searched for. Will return if there
    was no name found, as well.
    :rtype: str
    """
    person_name = next(
        (
            person.get("label")
            for person in persons
            if person.get("person_id") == to_delete
        ),
        None,
    )
    return person_name or "No name provided"


def run_people():
    """
    Allows the program to be ran if being imported as a module.

    :return: Returns the value 1 if the program completed successfully.
    :rtype: int
    """
    log.info("Retrieving persons")
    persons = get_people()
    log.info("persons retrieved.")

    if persons := sorted(persons, key=lambda x: x["person_id"]):
        handle_people(persons)
    else:
        log.warning("No persons were found.")

    return 1  # Completed


def handle_people(persons):
    """
    Handle the processing of people by gathering IDs, searching for
    safe people, and deleting people if needed.

    Args:
        persons: The list of people to handle.

    Returns:
        None
    """
    log.info("Person - Gather IDs")
    all_person_ids = get_people_ids(persons)
    all_person_ids = clean_list(all_person_ids)
    log.info("Person - IDs acquired.")

    log.info("Searching for safe persons.")
    safe_person_ids = [
        get_person_id(person, persons) for person in PERSISTENT_PERSONS
    ]
    safe_person_ids = clean_list(safe_person_ids)

    log.info("Safe persons found.")

    if persons_to_delete := [
        person for person in all_person_ids if person not in safe_person_ids
    ]:
        check_people(safe_person_ids, persons_to_delete, persons)
    else:
        log.info("-------------------------------")
        log.info(
            "The organization has already been purged.\
There are no more persons to delete."
        )
        log.info("-------------------------------")


##############################################################################
############################  All things plates  #############################
##############################################################################


def check_plates(safe, to_delete, plates):
    """
    Checks with the user before continuing with the purge.

    :param safe: Plates that are marked as safe during the purge.
    :type safe: list
    :param to_delete: Plates that are marked to be deleted during the purge.
    :type to_delete: list
    :param plates: A list of all plates found in a Verkada organization.
    :type plates: list
    """
    trust_level = None  # Pre-define
    ok = None  # Pre-define

    while trust_level not in ["1", "2", "3"]:
        print(
            "1. Check marked persistent plates against what the \
application found."
        )
        print("2. Check what is marked for deletion by the application.")
        print("3. Trust the process and blindly move forward.")

        trust_level = str(input("- ")).strip()

        if trust_level == "1":
            print("-------------------------------")
            print("Please check that the two lists match: ")

            safe_names = [
                print_plate_name(plate_id, plates) for plate_id in safe
            ]

            print(", ".join(safe_names))
            print("vs")
            print(", ".join(PERSISTENT_PLATES))
            print("-------------------------------")

            while ok not in ["y", "n"]:
                ok = str(input("Do they match?(y/n) ")).strip().lower()

                if ok == "y":
                    purge_plates(to_delete, plates)

                elif ok == "n":
                    print("Please check the input values")
                    print("Exiting...")

                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

        elif trust_level == "2":
            print("-------------------------------")
            print("Here are the plates being purged: ")

            delete_names = [
                print_plate_name(plate_id, plates) for plate_id in to_delete
            ]
            print(", ".join(delete_names))
            print("-------------------------------")

            while ok not in ["y", "n"]:
                ok = str(input("Is this list accurate?(y/n) ")).strip().lower()

                if ok == "y":
                    purge_plates(to_delete, plates)

                elif ok == "n":
                    print("Please check the input values.")
                    print("Exiting...")

                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

        elif trust_level == "3":
            print("Good luck!")
            purge_plates(to_delete, plates)

        else:
            print("Invalid input. Please enter '1', '2', or '3'.")


def get_plates(org_id=ORG_ID, api_key=API_KEY):
    """
    Returns JSON-formatted plates in a Command org.

    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: A List of dictionaries of license plates in an organization.
    :rtype: list
    """
    headers = {"accept": "application/json", "x-api-key": api_key}

    params = {
        "org_id": org_id,
    }

    response = requests.get(
        PLATE_URL, headers=headers, params=params, timeout=5
    )

    if response.status_code == 200:
        data = response.json()  # Parse the response

        # Extract as a list
        plates = data.get("license_plate_of_interest")

        try:
            # Check if the list is iterable
            iter(plates)
        except (TypeError, AttributeError):
            log.error("Plates are not iterable.")
            return

        return plates
    else:
        log.critical(
            "Plate - Error with retrieving plates. Status code %s",
            response.status_code,
        )
        return


def get_plate_ids(plates=None):
    """
    Returns an array of all LPoI labels in an organization.

    :param plates: A list of dictionaries representing LPoIs in an
    organization. Each dictionary should have 'license_plate' key.
    Defaults to None.
    :type plates: list, optional
    :return: A list of IDs of the LPoIs in an organization.
    :rtype: list
    """
    plate_id = []

    for plate in plates:
        if plate.get("license_plate"):
            plate_id.append(plate.get("license_plate"))
        else:
            log.error(
                "Plate - There has been an error with plate %s.",
                plate.get("label"),
            )

    return plate_id


def get_plate_id(plate, plates=None):
    """
    Returns the Verkada ID for a given LPoI.

    :param plate: The label of a LPoI whose ID is being searched for.
    :type plate: str
    :param plates: A list of LPoI IDs found inside of an organization.
    Each dictionary should have the 'license_plate' key. Defaults to None.
    :type plates: list, optional
    :return: The plate ID of the given LPoI.
    :rtype: str
    """
    if plate_id := next(
        (
            name["license_plate"]
            for name in plates
            if name["description"] == plate
        ),
        None,
    ):
        return plate_id
    log.error("Plate %s was not found in the database...", plate)
    return None


def delete_plate(plate, plates, org_id=ORG_ID, api_key=API_KEY):
    """
    Deletes the given plate from the organization.

    :param plate: The plate to be deleted.
    :type plate: str
    :param plates: A list of LPoI IDs found inside of an organization.
    :type plates: list
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: None
    :rtype: None
    """
    local_data = threading.local()
    local_data.RETRY_DELAY = DEFAULT_RETRY_DELAY

    headers = {"accept": "application/json", "x-api-key": api_key}

    log.info("Running for plate: %s", print_plate_name(plate, plates))

    params = {"org_id": org_id, "license_plate": plate}

    try:
        for _ in range(MAX_RETRIES):
            response = requests.delete(
                PLATE_URL, headers=headers, params=params, timeout=5
            )

            if response.status_code == 429:
                log.info(
                    "%s response: 429. Retrying in %ss.",
                    print_plate_name(plate, plates),
                    local_data.RETRY_DELAY,
                )

                time.sleep(local_data.RETRY_DELAY)

                local_data.RETRY_DELAY += BACKOFF

            else:
                break

        if response.status_code == 429:
            raise custom_exceptions.APIThrottleException("API throttled")

        elif response.status_code == 504:
            log.warning(
                "Plate - %s Timed out.", print_plate_name(plate, plates)
            )

        elif response.status_code == 400:
            log.warning("Plate - Contact support: endpoint failure")

        elif response.status_code != 200:
            log.error(
                "Plate - An error has occurred. Status code %s",
                response.status_code,
            )

    except custom_exceptions.APIThrottleException:
        log.critical(
            "Plate - Hit API request rate limit of 500 requests per minute."
        )


def purge_plates(delete, plates, org_id=ORG_ID, api_key=API_KEY):
    """
    Purges all LPoIs that aren't marked as safe/persistent.

    :param delete: A list of LPoIs to be deleted from the organization.
    :type delete: list
    :param plates: A list of LPoIs found inside of an organization.
    :type plates: list
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: Returns the value of 1 if completed successfully.
    :rtype: int
    """

    if not delete:
        log.warning("Plate - There's nothing here")
        return

    log.info("Plate - Purging...")

    plate_start_time = time.time()
    threads = []
    for plate in delete:
        # Toss delete function into a new thread
        thread = threading.Thread(
            target=delete_plate,
            args=(
                plate,
                plates,
                org_id,
                api_key,
            ),
        )
        threads.append(thread)  # Add the thread to the pile

    run_thread_with_rate_limit(threads)

    plate_end_time = time.time()
    plate_elapsed_time = plate_end_time - plate_start_time

    log.info("Plate - Purge complete.")
    log.info("Plate - Time to complete: %.2f", plate_elapsed_time)

    return 1  # Completed


def print_plate_name(to_delete, plates):
    """
        Returns the description of a LPoI with a given ID

        :param to_delete: The person ID whose name is being searched for in the
    dictionary.
        :type to_delete: str
        :param persons: A list of PoIs found inside of an organization.
        :type persons: list
        :return: Returns the name of the person searched for. Will return if there
    was no name found, as well.
        :rtype: str
    """
    plate_name = next(
        (
            plate.get("description")
            for plate in plates
            if plate.get("license_plate") == to_delete
        ),
        None,
    )
    return plate_name or "No name provided"


def run_plates():
    """
    Allows the program to be ran if being imported as a module.

    :return: Returns the value 1 if the program completed successfully.
    :rtype: int
    """
    log.info("Retrieving plates")
    plates = get_plates()
    log.info("Plates retrieved.")

    if plates := sorted(plates, key=lambda x: x["license_plate"]):
        handle_plates(plates)
    else:
        log.warning("No plates were found.")

    return 1  # Completed


def handle_plates(plates):
    """
    Handle the processing of plates by gathering IDs, searching for safe
    plates, and deleting plates if needed.

    Args:
        plates: The list of plates to handle.

    Returns:
        None
    """
    log.info("Plate - Gather IDs")
    all_plate_ids = get_plate_ids(plates)
    all_plate_ids = clean_list(all_plate_ids)
    log.info("Plate - IDs acquired.")

    log.info("Searching for safe plates.")
    safe_plate_ids = [
        get_plate_id(plate, plates) for plate in PERSISTENT_PLATES
    ]
    safe_plate_ids = clean_list(safe_plate_ids)

    log.info("Safe plates found.")

    if plates_to_delete := [
        plate for plate in all_plate_ids if plate not in safe_plate_ids
    ]:
        check_plates(safe_plate_ids, plates_to_delete, plates)
    else:
        log.info("-------------------------------")
        log.info(
            "The organization has already been purged.\
There are no more plates to delete."
        )
        log.info("-------------------------------")


##############################################################################
#  Main  #
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    warn()

    ANSWER = None
    while ANSWER not in ["y", "n"]:
        ANSWER = (
            str(input("Would you like to run for PoI?\n(y/n) "))
            .strip()
            .lower()
        )

        if ANSWER == "y":
            run_people()

            ANSWER = None

            while ANSWER not in ["y", "n"]:
                ANSWER = (
                    str(input("Would you like to run for LPoI?\n(y/n) "))
                    .strip()
                    .lower()
                )

                if ANSWER == "y":
                    run_plates()

                elif ANSWER == "n":
                    print("Exiting...")

        elif ANSWER == "n":
            ANSWER = None

            while ANSWER not in ["y", "n"]:
                ANSWER = (
                    str(input("Would you like to run for LPoI?\n(y/n) "))
                    .strip()
                    .lower()
                )

                if ANSWER == "y":
                    run_plates()

                elif ANSWER == "n":
                    print("Why did you run this?")
                    print("Exiting...")
