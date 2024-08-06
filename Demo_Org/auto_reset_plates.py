"""
Author: Ian Young
Purpose: Compare plates to a pre-defined array of names.
These names will be "persistent plates/persons" which are to remain in
Command. Any person or plate not marked thusly will be deleted from the org.
"""

# Import essential libraries
import datetime
import logging
import os
import threading
import time
from typing import Dict, List, Optional, Union

import requests
from tqdm import tqdm

import QoL.custom_exceptions as custom_exceptions

# Set timeout for a 429
MAX_RETRIES = 10
DEFAULT_RETRY_DELAY = 0.25
BACKOFF = 0.25

# Set logger
log = logging.getLogger()
log.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

if ORG_ID := os.environ.get("ORG_ID"):
    log.debug("ID retrieved.")

if API_KEY := os.environ.get("API_KEY"):
    log.debug("Key retrieved.")

try:
    import RPi.GPIO as GPIO  # type: ignore

    WORK_PIN = 7
    LPOI_PIN = 13
    POI_PIN = 11

    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(WORK_PIN, GPIO.OUT)
    except RuntimeError:
        GPIO = None
        log.debug("Runtime error while initializing GPIO board.")
except ImportError:
    GPIO = None
    log.debug("RPi.GPIO is not available. Running on a non-Pi platform")

# Set the full name for which plates are to be persistent
PERSISTENT_PLATES = sorted([""])  # Label of plate #!Not plate number!#
PERSISTENT_PERSONS = sorted(["Parkour"])  # PoI label
PERSISTENT_PID = sorted(["751e9607-4617-43e1-9e8c-1bd439c116b6"])  # PoI ID
PERSISTENT_LID = sorted([""])  # LPoI ID

# Set API endpoint URLs
PLATE_URL = "https://api.verkada.com/cameras/v1/\
analytics/lpr/license_plate_of_interest"
PERSON_URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"


##############################################################################
##################################  Misc  ####################################
##############################################################################


class RateLimiter:
    """
    The purpose of this class is to limit how fast multi-threaded actions are
    created to prevent hitting the API limit.
    """

    def __init__(
        self, rate_limit: int, max_events_per_sec: int = 5, pacing: int = 1
    ):
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
        self.start_time: float = 0
        self.event_count = 0

    def acquire(self) -> bool:
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


def run_thread_with_rate_limit(
    threads: List[threading.Thread], rate_limit: int = 5
):
    """
    Run a thread with rate limiting.

    :param target: The target function to be executed in the thread:
    :type targe: function:
    :return: The thread that was created and ran
    :rtype: thread
    """
    limiter = RateLimiter(rate_limit=rate_limit)
    progress_bar = tqdm(total=len(threads), desc="Processing plates")

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
        progress_bar.update(1)

    progress_bar.close()


def clean_list(messy_list):
    """
    Removes any None values from error codes

    :param list: The list to be cleaned.
    :type list: list
    :return: A new list with None values removed.
    :rtype: list
    """
    return [value for value in messy_list if value is not None]


def flash_led(pin, local_stop_event, speed):
    """
    Flashes an LED that is wired into the GPIO board of a raspberry pi for
    the duration of work.

    :param pin: target GPIO pin on the board.
    :type pin: int
    :param local_stop_event: Thread-local event to indicate when the program's
    work is done and the LED can stop flashing.
    :type local_stop_event: Bool
    :param speed: How long each flash should last in seconds.
    :type failed: int
    :return: None
    :rtype: None
    """
    while not local_stop_event.is_set():
        GPIO.output(pin, True)
        time.sleep(speed)
        GPIO.output(pin, False)
        time.sleep(speed * 2)


##############################################################################
############################  All things plates  #############################
##############################################################################


def get_plates(
    org_id: Optional[str] = ORG_ID, api_key: Optional[str] = API_KEY
) -> Optional[List[str]]:
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
            return None

        return plates
    else:
        log.critical(
            "Plate - Error with retrieving plates. Status code %s",
            response.status_code,
        )
        return None


def get_plate_ids(
    plates: Optional[List[Dict[str, str]]] = None
) -> List[Optional[str]]:
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

    if plates:
        for plate in plates:
            if plate.get("license_plate"):
                plate_id.append(plate.get("license_plate"))
            else:
                log.error(
                    "Plate - There has been an error with plate %s.",
                    plate.get("label"),
                )
    else:
        log.error("No list was provided")

    return plate_id


def get_plate_id(
    plate: Optional[Union[str, List[str]]] = PERSISTENT_PLATES,
    plates: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
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
    if plates and (
        plate_id := next(
            (
                name["license_plate"]
                for name in plates
                if name["description"] == plate
            ),
            None,
        )
    ):
        return plate_id

    log.error("Plate %s was not found in the database...", plate)

    return None


def delete_plate(
    plate: str,
    plates: List[Dict[str, str]],
    org_id: Optional[str] = ORG_ID,
    api_key: Optional[str] = API_KEY,
):
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


def purge_plates(
    delete: List[Optional[str]],
    plates: List[Dict[str, str]],
    org_id: Optional[str] = ORG_ID,
    api_key: Optional[str] = API_KEY,
):
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

    local_stop_event = threading.Event()

    if GPIO and LPOI_PIN:
        flash_thread = threading.Thread(
            target=flash_led,
            args=(
                LPOI_PIN,
                local_stop_event,
                0.5,
            ),
        )
        flash_thread.start()

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

    if GPIO and LPOI_PIN:
        local_stop_event.set()
        flash_thread.join()


def print_plate_name(to_delete: str, plates: List[Dict[str, str]]) -> str:
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
        log.info("No plates were found.")


def handle_plates(plates: List[Dict[str, str]]):
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

    if PERSISTENT_LID:
        for plate in PERSISTENT_LID:
            safe_plate_ids.append(plate)
    log.info("Safe plates found.")

    if plates_to_delete := [
        plate for plate in all_plate_ids if plate not in safe_plate_ids
    ]:
        purge_plates(plates_to_delete, plates)
    else:
        log.info(
            "The organization has already been purged.\
There are no more plates to delete."
        )


##############################################################################
###################################  Main  ###################################
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    if GPIO:
        GPIO.output(WORK_PIN, True)

    start_time = time.time()
    LPoI = threading.Thread(target=run_plates)

    # Start the threads running independently
    LPoI.start()

    # Join the threads back to parent process
    LPoI.join()
    elapsed_time = time.time() - start_time
    if GPIO:
        GPIO.output(WORK_PIN, False)

    log.info("Total time to complete: %.2fs", elapsed_time)
