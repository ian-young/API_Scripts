"""
Author: Ian Young
Purpose: Compare plates to a pre-defined array of names.
These names will be "persistent" which are to remain in Command.
Anything not marked thusly will be deleted from the org.
"""
import datetime
import logging
import threading
import time
from os import getenv

from dotenv import load_dotenv

import reset_poi as poi
import reset_lpoi as lpoi
import reset_users as account

load_dotenv()  # Load credentials file

ORG_ID = getenv("")
API_KEY = getenv("")

# Set timeout for a 429
MAX_RETRIES = 10
DEFAULT_RETRY_DELAY = 0.25
BACKOFF = 0.25

# Set logger
log = logging.getLogger()
logging.basicConfig(
    level = logging.INFO,
    format = "%(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)


# Set the full name for which plates are to be persistent
PERSISTENT_PLATES = sorted([])  # Label of plate #!Not plate number!#
PERSISTENT_PERSONS = sorted(['Parkour'])  # PoI label
PERSISTENT_USERS = sorted(["Ian Young", "Bruce Banner",
                    "Jane Doe", "Tony Stark",
                    "Ray Raymond", "John Doe"]) # Must use full name
PERSISTENT_PID = sorted(["751e9607-4617-43e1-9e8c-1bd439c116b6"])  # PoI ID
PERSISTENT_LID = sorted([])  # LPoI ID

# Set API endpoint URLs
PLATE_URL = "https://api.verkada.com/cameras/v1/analytics/lpr/license_plate_of_interest"
PERSON_URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"
USER_INFO_URL = "https://api.verkada.com/access/v1/access_users"
USER_CONTROL_URL = "https://api.verkada.com/core/v1/user"


##############################################################################
                                #  Misc  #
##############################################################################


class RateLimiter:
    """
    The purpose of this class is to limit how fast multi-threaded actions are
    created to prevent hitting the API limit.
    """

    def __init__(self, rate_limit, max_events_per_sec=5, pacing=1):
        """
        Initilization of the rate limiter.

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

            if not hasattr(self, 'start_time'):
                # Check if attribue 'start_time' exists, if not, make it.
                self.start_time = current_time
                self.event_count = self.pacing
                return True

            # How much time has passed since starting
            elapsed_since_start = current_time - self.start_time

            # Check if it's been less than 1sec and less than 10 events have
            # been made.
            if elapsed_since_start < self.pacing / self.rate_limit \
                    and self.event_count < self.max_events_per_sec:
                self.event_count += 1
                return True

            # Check if it is the first wave of events
            elif elapsed_since_start >= self.pacing / self.rate_limit:
                self.start_time = current_time
                self.event_count = 2
                return True

            else:
                # Calculate the time left before next wave
                remaining_time = self.pacing - \
                    (current_time - self.start_time)
                time.sleep(remaining_time)  # Wait before next wave
                return True


def run_thread_with_rate_limit(threads, rate_limit=5):
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
            datetime.datetime.now().strftime('%H:%M:%S')
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
        cont = str(input("Press enter to continue")).strip()


def clean_list(messy_list):
    """Removes any None values from error codes"""
    cleaned_list = [value for value in messy_list if value is not None]
    return cleaned_list


##############################################################################
                         #  All things people  #
##############################################################################

def run_people():
    """
    Allows the program to be ran if being imported as a module.

    :return: Returns the value 1 if the program completed successfully.
    :rtype: int
    """
    log.info("Retrieving persons")
    persons = poi.get_people()
    log.info("persons retrieved.")

    # Sort JSON dictionaries by person id
    persons = sorted(persons, key=lambda x: x['person_id'])

    # Run if persons were found
    if persons:
        log.info("Person - Gather IDs")
        all_person_ids = poi.get_people_ids(persons)
        all_person_ids = clean_list(all_person_ids)
        log.info("Person - IDs aquired.")

        safe_person_ids = []

        log.info("Searching for safe persons.")
        # Create the list of safe persons
        for person in PERSISTENT_PERSONS:
            safe_person_ids.append(poi.get_person_id(person, persons))
        safe_person_ids = clean_list(safe_person_ids)

        if PERSISTENT_PID:
            for person in PERSISTENT_PID:
                safe_person_ids.append(person)
        log.info("Safe persons found.")

        # New list that filters persons that are safe
        persons_to_delete = [
            person for person in all_person_ids
            if person not in safe_person_ids]

        if persons_to_delete:
            poi.check(safe_person_ids, persons_to_delete, persons)
            return 1  # Completed

        else:
            log.info(
                "Person - The organization has already been purged.\
There are no more persons to delete.")

            return 1  # Completed
    else:
        log.warning("No persons were found.")

        return 1  # Copmleted


##############################################################################
                            #  All things plates  #
##############################################################################


def run_plates():
    """
    Allows the program to be ran if being imported as a module.

    :return: Returns the value 1 if the program completed successfully.
    :rtype: int
    """
    log.info("Retrieving plates")
    plates = lpoi.get_plates()
    log.info("Plates retrieved.")

    # Sort the JSON dictionaries by plate id
    plates = sorted(plates, key=lambda x: x['license_plate'])

    # Run if plates were found
    if plates:
        log.info("Plate - Gather IDs")
        all_plate_ids = lpoi.get_plate_ids(plates)
        all_plate_ids = clean_list(all_plate_ids)
        log.info("Plate - IDs aquired.")

        safe_plate_ids = []

        log.info("Searching for safe plates.")
        # Create the list of safe plates
        for plate in PERSISTENT_PLATES:
            safe_plate_ids.append(lpoi.get_plate_id(plate, plates))
        safe_plate_ids = clean_list(safe_plate_ids)

        if PERSISTENT_LID:
            for plate in PERSISTENT_LID:
                safe_plate_ids.append(plate)
        log.info("Safe plates found.")

        # New list that filters plates that are safe
        plates_to_delete = [
            plate for plate in all_plate_ids if plate not in safe_plate_ids
        ]

        if plates_to_delete:
            lpoi.check(safe_plate_ids, plates_to_delete, plates)
            return 1  # Completed

        else:
            log.info(
                "The organization has already been purged.\
There are no more plates to delete.")

            return 1  # Completed
    else:
        log.info("No plates were found.")

        return 1  # Completed


##############################################################################
                            #  All things users  #
##############################################################################


def run_users():
    """
    Allows the program to be ran if being imported as a module
    
    :return: Returns the value 1 if the program completed successfully.
    :rtype: int
    """
    log.info("Retrieving users")
    users = account.get_users()
    log.info("Users retrieved.\n")

    # Run if users were found
    if users:
        log.info("Gather IDs")
        all_user_ids = account.get_ids(users)
        all_user_ids = clean_list(all_user_ids)
        log.info("IDs aquired.\n")

        safe_user_ids = []

        # Create the list of safe users
        log.info("Searching for safe users.")
        for user in PERSISTENT_USERS:
            safe_user_ids.append(account.get_user_id(user, users))
        safe_user_ids = clean_list(safe_user_ids)
        log.info("Safe users found.\n")

        # New list that filters users that are safe
        users_to_delete = [
            user for user in all_user_ids if user not in safe_user_ids]

        if users_to_delete:
            purge_manager = account.PurgeManager(call_count_limit=300)
            account.check(
                safe_user_ids, users_to_delete, users, purge_manager)
            return 1  # Completed

        else:
            log.info("-------------------------------")
            log.info(
                "The organization has already been purged."
                "There are no more users to delete."
            )
            log.info("-------------------------------")

            return 1  # Completed
    else:
        log.warning("No users were found.")

        return 1  # Copmleted


##############################################################################
                                #  Main  #
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    warn()

    poi_thread = threading.Thread(target=run_people)
    lpoi_thread = threading.Thread(target=run_plates)
    user_thread = threading.Thread(target=run_users)

    ANSWER = None
    while ANSWER not in ['y', 'n']:
        ANSWER = str(input("Would you like to run for users?(y/n) "))\
        .strip().lower()

        if ANSWER == 'y':
            RUN_USER = True

    ANSWER = None
    while ANSWER not in ['y', 'n']:
        ANSWER = str(input("Would you like to run for PoI?(y/n) "))\
            .strip().lower()

        if ANSWER == 'y':
            RUN_POI = True

    ANSWER = None
    while ANSWER not in ['y', 'n']:
        ANSWER = str(input("Would you like to run for LPoI?(y/n) "))\
            .strip().lower()

        if ANSWER == 'y':
            RUN_LPOI = True

    # Time the runtime
    start_time = time.time()

    # Start threads
    if RUN_USER:
        user_thread.start()
    if RUN_POI:
        poi_thread.start()
    if RUN_LPOI:
        lpoi_thread.start()

    # Join back to main thread
    if RUN_USER:
        user_thread.join()
    if RUN_POI:
        poi_thread.join()
    if RUN_LPOI:
        lpoi_thread.join()

    # Wrap up in a bow and complete
    log.info(
        "Time to complete: %.2fs.",
        time.time() - start_time
    )
    print("Exiting...")
