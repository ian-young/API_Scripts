"""
Author: Ian Young
Purpose: Test Verkada API endpoints.
This script is to be ran using the pip module pytest
Anything that starts with test will be ran by pytest
The script only looks for a 200 response code.
"""

# Import essential libraries
import base64
import logging
import re
import shutil
import threading
import time
from datetime import datetime, timedelta
from os import getenv

import colorama
import requests
from colorama import Fore, Style
from dotenv import load_dotenv

# Set log file path
LOG_FILE_PATH = "endpoint_data.log"

# Set logger
log = logging.getLogger()
log.setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE_PATH), logging.StreamHandler()],
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

try:
    import RPi.GPIO as GPIO  # type: ignore

    RETRY_PIN = 11
    FAIL_PIN = 13
    RUN_PIN = 7
    SUCCESS_PIN = 15

    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(RUN_PIN, GPIO.OUT)
        GPIO.setup(RETRY_PIN, GPIO.OUT)
        GPIO.setup(FAIL_PIN, GPIO.OUT)
        if SUCCESS_PIN:
            GPIO.setup(SUCCESS_PIN, GPIO.OUT)
    except RuntimeError:
        GPIO = None
        log.debug("GPIO Runtime error")
except ImportError:
    GPIO = None
    log.debug("RPi.GPIO is not available. Running on a non-Pi platform")

colorama.init(autoreset=True)

# Set URLs
URL_PEOPLE = "https://api.verkada.com/cameras/v1/people/person_of_interest"
URL_PLATE = "https://api.verkada.com/cameras/v1/analytics/lpr/license_plate\
_of_interest"
URL_CLOUD = "https://api.verkada.com/cameras/v1/cloud_backup/settings"
URL_OBJ = "https://api.verkada.com/cameras/v1/analytics/object_counts"
URL_MQTT = "https://api.verkada.com/cameras/v1/analytics/object_position_mqtt"
URL_OCCUPANCY = "https://api.verkada.com/cameras/v1/analytics/occupancy_trends"
URL_DEVICES = "https://api.verkada.com/cameras/v1/devices"
URL_FOOTAGE = "https://api.verkada.com/cameras/v1/footage/thumbnails/latest"
URL_AUDIT = "https://api.verkada.com/core/v1/audit_log"
URL_CORE = "https://api.verkada.com/core/v1/user"
URL_AC_GROUPS = "https://api.verkada.com/access/v1/access_groups"
URL_AC_USERS = "https://api.verkada.com/access/v1/access_users"
URL_AC_CRED = "https://api.verkada.com/access/v1/credentials/card"
URL_AC_PLATE = "https://api.verkada.com/access/v1/credentials/license_plate"
URL_TOKEN = "https://api.verkada.com/cameras/v1/footage/token"
URL_TOKEN = "https://api.verkada.com/cameras/v1/footage/token"

load_dotenv()

load_dotenv()  # Load credentials file

# Set general testing variables
ORG_ID = getenv("")  # Org ID
API_KEY = getenv("")  # API key
STREAM_API_KEY = getenv("")  # API key with streaming permissions
CAMERA_ID = getenv("")  # Device ID of camera
TEST_USER = getenv("")  # Command User ID
TEST_USER_CRED = getenv("")  # Command user to test AC changes
CARD_ID = getenv("")  # Card ID to manipulate
PLATE = getenv("")  # AC plate cred to manipulate

GENERAL_HEADER = {"accept": "application/json", "x-api-key": API_KEY}

FAILED_ENDPOINTS = []
FAILED_ENDPOINTS_LOCK = threading.Lock()
MAX_RETRIES = 5  # How many times the program should retry on 429
RETRY_DELAY = 0.25  # Seconds to wait
RETRY_COUNT = 0
RETRY_COUNT_LOCK = threading.Lock()


##############################################################################
##################################  Misc  ####################################
##############################################################################


class RateLimiter:
    """
    The purpose of this class is to limit how fast multi-threaded actions are
    created to prevent hitting the API limit.
    """

    def __init__(self, rate_limit, max_events_per_sec=5, pacing=1):
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


def run_thread_with_rate_limit(new_threads, rate_limit=5):
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
            datetime.now().strftime("%H:%M:%S"),
        )
        thread.start()

    for thread in new_threads:
        run_thread(thread)

    for thread in new_threads:
        thread.join()


def print_colored_centered(runtime, tests_passed, failed, failed_modules):
    """
    Formats and prints what modules failed and how long it took for the
    program to complete all the tests.

    :param runtime: The time it took for the program to complete.
    :type runtime: int
    :param passed: How many modules passed their tests.
    :type passed: int
    :param failed: How many modules failed their tests.
    :type failed: int
    :param failed_modules: The name of the modules that failed their tests.
    :type failed_modules: list
    :return: None
    :rtype: None
    """
    rthread = threading.Thread(target=flash_led, args=(RETRY_PIN, RETRY_COUNT))
    fthread = threading.Thread(target=flash_led, args=(FAIL_PIN, failed))
    sthread = threading.Thread(
        target=flash_led, args=(SUCCESS_PIN, tests_passed)
    )

    terminal_width, _ = shutil.get_terminal_size()
    short_time = round(runtime, 2)

    # text1 = f"{Fore.CYAN} short test summary info "
    text2_fail = f"{Fore.RED} {failed} failed, {Fore.GREEN}{tests_passed} \
passed{Fore.RED} in {short_time}s "
    text2_pass = f"{Fore.GREEN} {tests_passed} passed in \
{short_time}s "
    text2_fail_retry = f"{Fore.RED} {failed} failed, {Fore.GREEN}\
{tests_passed}passed{Fore.RED},{Fore.YELLOW} {RETRY_COUNT} retries\
{Fore.RED} in {short_time}s "
    text2_pass_retry = f"{Fore.GREEN} {tests_passed} passed,{Fore.YELLOW} \
{RETRY_COUNT} retries{Fore.GREEN} in {short_time}s "

    # Print the padded and colored text with "=" characters on both sides
    # An extra line that can be printed if running in live terminal
    # print(f"{Fore.CYAN}{text1:=^{terminal_width+5}}")

    if failed > 0:
        for module in failed_modules:
            print(f"{Fore.RED}FAILED {Style.RESET_ALL}{module}")

        if RETRY_COUNT > 0:
            print(f"{Fore.RED}{text2_fail_retry:=^{terminal_width+25}}")
            rthread.start()
            fthread.start()
            sthread.start()
            sthread.join()
            rthread.join()
        else:
            print(f"{Fore.RED}{text2_fail:=^{terminal_width+15}}")
            sthread.start()
            fthread.start()
            sthread.join()
        fthread.join()
    else:
        if RETRY_COUNT > 0:
            print(f"{Fore.GREEN}{text2_pass_retry:=^{terminal_width+15}}")
            rthread.start()
            sthread.start()
            rthread.join()
        else:
            print(f"{Fore.GREEN}{text2_pass:=^{terminal_width+5}}")
            sthread.start()

        sthread.join()


def flash_led(pin, count, speed):
    """
    Flashes an LED that is wired into the GPIO board of a raspberry pi

    :param pin: target GPIO pin on the board.
    :type pin: int
    :param count: How many times the LED should flash.
    :type passed: int
    :param speed: How long each flash should last in seconds.
    :type failed: int
    :return: None
    :rtype: None
    """
    for _ in range(count):
        GPIO.output(pin, True)
        time.sleep(speed)
        GPIO.output(pin, False)
        time.sleep(speed)


def work_led(pin, stop_event, speed):
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
    while not stop_event.is_set():
        GPIO.output(pin, True)
        time.sleep(speed)
        GPIO.output(pin, False)
        time.sleep(speed * 2)


def log_execution():
    """
    Writes the final output from running the program into a file to ingest
    later to plot the results.
    """
    # Save all current entries in the file before changing
    with open(LOG_FILE_PATH, "r", encoding="utf-8") as log_file:
        entries = log_file.readlines()

    # Filter out anything older than 24-hours
    filtered_entries = filter_entries(entries)

    # Overwrite the original file with the filtered entries
    with open("endpoint_data.log", "w", encoding="utf-8") as file:
        file.writelines(filtered_entries)

    # Append the new data to the file
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(
            f"Time of execution: "
            f"{datetime.now().strftime('%m/%d %H:%M:%S')}\n"
        )
        log_file.write(f"Failed endpoints: {len(FAILED_ENDPOINTS)}\n")
        log_file.write(f"Retries: {RETRY_COUNT}\n")


def parse_entry(entry):
    """
    Parse the data of data given a file.

    :param entry: The text read line-by-line in a file.
    :type entry: str
    :return: The formatted time for the entry file.
    :rtype: datetime
    """
    if time_match := re.search(r"(\d{2}/\d{2} \d{2}:\d{2}:\d{2})", entry):
        time_str = time_match[1]
        # Set the year to the current year
        current_year = datetime.now().year
        return datetime.strptime(
            f"{current_year} {time_str}", "%Y %m/%d %H:%M:%S"
        )


def filter_entries(entries):
    """
    Parse the data of data given a file.

    :param entries: The text read line-by-line in a file.
    :type entries: str
    :return: The formatted time for the entry file.
    :rtype: datetime
    """
    filtered_entries = []
    current_time = datetime.now()

    include_entry = False

    for entry in entries:
        if execution_time := parse_entry(entry):
            time_difference = current_time - execution_time

            # Check if the entry is within the last 24 hours
            if time_difference < timedelta(days=1):
                include_entry = True
                filtered_entries.append(entry)
            else:
                include_entry = False

        elif include_entry:
            filtered_entries.append(entry)

    return filtered_entries


##############################################################################
###############################  Test PoI  ###################################
##############################################################################


def test_poi():
    """Serves as a driver function for all POI tests."""
    create_poi()
    get_poi()
    update_poi()
    delete_poi()


def get_person_id():
    """
    Accepts a string as a search value and returns the person id
    associated with it

    :return: The person id for the search value hard-coded into label.
    :rtype: str
    """
    # Define query parameters for the request
    params = {"org_id": ORG_ID, "label": "test"}

    # Send a GET request to search for persons of interest
    response = requests.get(
        URL_PEOPLE, headers=GENERAL_HEADER, params=params, timeout=5
    )

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        if persons_of_interest := data.get("persons_of_interest", []):
            return persons_of_interest[0].get("person_id")
        else:
            log.warning("No person was found with the label 'test'.")


def create_poi():
    """
    Creates a PoI to test the responsiveness of the API endpoint.

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s create_poi", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    file_content = None  # Pre-define

    # Download the JPG file from the URL
    img_response = requests.get(
        "https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fi.pinimg\
.com%2F736x%2F87%2Fea%2F33%2F87ea336233db8ad468405db8f94da050--human-faces-\
photos-of.jpg&f=1&nofb=1&ipt=6af7ecf6cd0e15496e7197f3b6cb1527beaa8718c58609d4\
feca744209047e57&ipo=images",
        timeout=5,
    )

    if img_response.status_code == 200:
        # File was successfully downloaded
        file_content = img_response.content
    else:
        # Handle the case where the file download failed
        log.critical("Failed to download the image")

    # Convert the binary content to base64
    base64_image = base64.b64encode(file_content).decode("utf-8")

    # Set payload
    payload = {"label": "test", "base64_image": base64_image}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY,
    }

    params = {"org_id": ORG_ID}

    for _ in range(MAX_RETRIES):
        response = requests.post(
            URL_PEOPLE, json=payload, headers=headers, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info("create_poi retrying in %ss. Response: 429", RETRY_DELAY)

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("create_poi response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append("create_poi: %d", response.status_code)


def get_poi():
    """
    Looks to see if it can get a list of PoIs

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s get_poi", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    params = {"org_id": ORG_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_PEOPLE, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info("get_poi retrying in %ds. Response: 429", RETRY_COUNT)

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("get_poi response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"get_poi: {response.status_code}")


def update_poi():
    """
    Tests the patch requests for the people endpoint

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s update_poi", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    payload = {"label": "Test"}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY,
    }

    # Define query parameters for the request
    params = {"org_id": ORG_ID, "person_id": get_person_id()}

    for _ in range(MAX_RETRIES):
        response = requests.patch(
            URL_PEOPLE, json=payload, headers=headers, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info("update_poi retrying in %ds. Response: 429", RETRY_DELAY)

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("update_poi response received: %d", response.status_code)

    if response.status_code == 400:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"get_person_id: {response.status_code}")
    elif response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"update_poi: {response.status_code}")


def delete_poi():
    """
    Tests the delete request for the people endpoint

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s delete_poi", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    headers = {"accept": "application/json", "x-api-key": API_KEY}

    params = {"org_id": ORG_ID, "person_id": get_person_id()}

    for _ in range(MAX_RETRIES):
        response = requests.delete(
            URL_PEOPLE, headers=headers, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info("delete_poi retrying in %ds. Response: 429", RETRY_DELAY)

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("delete_poi response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"delete_poi: {response.status_code}")


##############################################################################
#################################  Test LPoI  ################################
##############################################################################


def test_plates():
    """Serves as a driver function for all LPOI tests."""
    create_plate()
    get_plate()
    update_plate()
    delete_plate()


def create_plate():
    """
    Creates a Plate to test the API endpoint

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s create_plate", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    # Set payload
    payload = {"description": "test", "license_plate": "t3stpl4te"}

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY,
    }

    params = {"org_id": ORG_ID}

    for _ in range(MAX_RETRIES):
        response = requests.post(
            URL_PLATE, json=payload, headers=headers, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info(
                "create_plate retrying in %ds. Response: 429", RETRY_DELAY
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("create_plate response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"create_plate: {response.status_code}")


def get_plate():
    """
    Looks to see if it can get Plates

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s get_plate", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    headers = {"accept": "application/json", "x-api-key": API_KEY}

    params = {"org_id": ORG_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_PLATE, headers=headers, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info("get_plate retrying in %ds. Response: 429", RETRY_DELAY)

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("get_plates response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"get_plate: {response.status_code}")


def update_plate():
    """
    Tests the patch requests for the Plate endpoint

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s update_plate", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    payload = {"description": "Test"}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY,
    }

    # Define query parameters for the request
    params = {"org_id": ORG_ID, "license_plate": "t3stpl4te"}

    for _ in range(MAX_RETRIES):
        response = requests.patch(
            URL_PLATE, json=payload, headers=headers, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info(
                "update_plate retrying in %ds. Response: 429", RETRY_DELAY
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("update_plate response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"update_plate: {response.status_code}")


def delete_plate():
    """
    Tests the delete request for the Plate endpoint

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s delete_plate", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    params = {"org_id": ORG_ID, "license_plate": "t3stpl4te"}

    for _ in range(MAX_RETRIES):
        response = requests.delete(
            URL_PLATE, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info(
                "delete_plate retrying in %ds. Response: 429", RETRY_DELAY
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("delete_plate response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"delete_plate: {response.status_code}")


##############################################################################
###############################  Test Cameras  ###############################
##############################################################################


def get_cloud_settings():
    """
    Tests to see if it can retrieve cloud backup settings for a camera

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(
        "%sRunning%s get_cloud_settings", Fore.LIGHTBLACK_EX, Style.RESET_ALL
    )

    params = {"org_id": ORG_ID, "camera_id": CAMERA_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_CLOUD, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info(
                "get_cloud_settings retrying in %ds.\
 Response: 429",
                RETRY_DELAY,
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("get_cloud_settings response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(
                f"get_cloud_settings: \
{response.status_code}"
            )


def get_counts():
    """
    Tests if it can get object counts from a camera

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s get_counts", Fore.LIGHTBLACK_EX, Style.RESET_ALL)
    params = {"org_id": ORG_ID, "camera_id": CAMERA_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_OBJ, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info("get_counts retrying in %ds. Response: 429", RETRY_DELAY)

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("get_counts response received")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"get_counts: {response.status_code}")


def get_trendline_data():
    """
    Tests if it can get trend counts from a camera

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(
        "%sRunning%s get_trendline_data", Fore.LIGHTBLACK_EX, Style.RESET_ALL
    )

    params = {"org_id": ORG_ID, "camera_id": CAMERA_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_OCCUPANCY, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info(
                "get_trend_line_data retrying in %ds.\
 Response: 429",
                RETRY_DELAY,
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("getTrendLineData response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(
                f"get_trendline_data: {response.status_code}"
            )


def get_camera_data():
    """
    Tests if it can get camera data on a given camera

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(
        "%sRunning%s get_camera_data", Fore.LIGHTBLACK_EX, Style.RESET_ALL
    )

    params = {"org_id": ORG_ID, "camera_id": CAMERA_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_OCCUPANCY, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info(
                "get_camera_data retrying in %ds\
. Response: 429",
                RETRY_DELAY,
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("get_camera_data response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"get_camera_data: {response.status_code}")


def get_thumbed():
    """
    Tests if it can get a thumbnail from a camera

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s get_thumbnail", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    params = {
        "org_id": ORG_ID,
        "camera_id": CAMERA_ID,
        "resolution": "low-res",
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_FOOTAGE, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info(
                "getThumbnail retrying in %ds.\
 Response: 429",
                RETRY_DELAY,
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("getThumbnail response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getThumbnail: {response.status_code}")


##############################################################################
#################################  Test Core  ################################
##############################################################################


def get_audit_logs():
    """
    Tests the ability to retrieve audit logs

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s get_audit_logs", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    params = {"org_id": ORG_ID, "page_size": "1"}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_AUDIT, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info(
                "get_audit_logs retrying in %ds.\
 Response: 429",
                RETRY_DELAY,
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

        log.info(
            "get_audit_logsLogs response received: %d", response.status_code
        )

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"get_audit_logs: {response.status_code}")


def update_user():
    """
    Tests the ability to update a user

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s update_user", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    payload = {"active": False}

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY,
    }

    params = {"org_id": ORG_ID, "user_id": TEST_USER}

    for _ in range(MAX_RETRIES):
        response = requests.put(
            URL_CORE, json=payload, headers=headers, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info("update_user retrying in %ds. Response: 429", RETRY_DELAY)

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("update_user response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"update_user: {response.status_code}")


def get_user():
    """
    Tests the ability to retrieve information on a user

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info("%sRunning%s get_user", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    params = {"user_id": TEST_USER}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_CORE, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info("get_user retrying in %ds. Response: 429", RETRY_DELAY)

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("get_user response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"get_user: {response.status_code}")


def get_jwt(org_id=ORG_ID, api_key=STREAM_API_KEY):
    """
        Generates a JWT token for the streaming API. This token will be integrated
    inside of a link to grant access to footage.

        :param org_id: Organization ID. Defaults to ORG_ID.
        :type org_id: str, optional
        :param api_key: API key for authentication. Defaults to API_KEY.
        :type api_key: str, optional
        :return: Returns the JWT token to allow access via a link to footage.
        :rtype: str
    """
    global RETRY_COUNT

    log.info("%sRunning%s get_jwt", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    # Define the request headers
    headers = {"x-api-key": api_key}

    # Set the parameters of the request
    params = {"org_id": org_id, "expiration": 60}

    for _ in range(MAX_RETRIES):

        # Send GET request to get the JWT
        response = requests.get(
            URL_TOKEN, headers=headers, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info("get_jwt retrying in %ds. Response: 429", RETRY_DELAY)

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("get_jwt response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"get_jwt: {response.status_code}")


##############################################################################
##########################  Test Access Control  #############################
##############################################################################


def get_access_groups():
    """
    Tests the ability to get AC Groups

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(
        "%sRunning%s get_access_groups", Fore.LIGHTBLACK_EX, Style.RESET_ALL
    )

    params = {"org_id": ORG_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_AC_GROUPS, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info(
                "get_access_groups retrying in %ds. Response: 429", RETRY_DELAY
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("get_access_groups response received")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(
                f"get_access_groups: {response.status_code}"
            )


def get_access_users():
    """
    Tests the ability to get AC users

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(
        "%sRunning%s get_access_users", Fore.LIGHTBLACK_EX, Style.RESET_ALL
    )

    params = {"org_id": ORG_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_AC_USERS, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code == 429:
            log.info(
                "get_access_users retrying in %ds.\
 Response: 429",
                RETRY_DELAY,
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("get_access_users response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(
                f"get_access_users: {response.status_code}"
            )


def change_cards():
    """
    Tests the ability to change credentials

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(
        "%sRunning%s activate_card\
 & deactivate_card",
        Fore.LIGHTBLACK_EX,
        Style.RESET_ALL,
    )

    params = {"org_id": ORG_ID, "user_id": TEST_USER_CRED, "card_id": CARD_ID}

    activate_url = URL_AC_CRED + "/activate"
    deactivate_url = URL_AC_CRED + "/deactivate"

    for _ in range(MAX_RETRIES):
        active_response = requests.put(
            activate_url, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if active_response.status_code == 429:
            log.info(
                "activate_card retrying in %ds.\
 Response: 429",
                RETRY_DELAY,
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(
        "activate_card response received: %d", active_response.status_code
    )

    for _ in range(MAX_RETRIES):
        deactive_response = requests.put(
            deactivate_url, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if deactive_response.status_code == 429:
            log.info(
                "deactivate_card retrying in %ds.\
 Response: 429",
                RETRY_DELAY,
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(
        "deactivate_card response received: %d", deactive_response.status_code
    )

    if active_response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(
                f"activate_card: \
{active_response.status_code}"
            )

    elif deactive_response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(
                f"deactivate_card: \
{deactive_response.status_code}"
            )


def change_plates():
    """
    Tests the ability to change access plates

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(
        "%sRunning%s activatePlate & deactivatePlate",
        Fore.LIGHTBLACK_EX,
        Style.RESET_ALL,
    )

    params = {
        "org_id": ORG_ID,
        "user_id": TEST_USER_CRED,
        "license_plate_number": PLATE,
    }

    activate_url = URL_AC_PLATE + "/activate"
    deactivate_url = URL_AC_PLATE + "/deactivate"

    for _ in range(MAX_RETRIES):
        active_response = requests.put(
            activate_url, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if active_response.status_code == 429:
            log.info(
                "activatePlate retrying in %ds.\
 Response: 429",
                RETRY_DELAY,
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(
        "activatePlate response received: %d", active_response.status_code
    )

    for _ in range(MAX_RETRIES):
        deactive_response = requests.put(
            deactivate_url, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if deactive_response.status_code == 429:
            log.info(
                "deactivatePlate retrying in %ds.\
 Response: 429",
                RETRY_DELAY,
            )

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(
        "deactivatePlate response received: %d", deactive_response.status_code
    )

    if active_response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(
                f"activatePlate: \
{active_response.status_code}"
            )

    elif deactive_response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(
                f"deactivatePlate: \
{deactive_response.status_code}"
            )


##############################################################################
##################################  Main  ####################################
##############################################################################

if __name__ == "__main__":
    print(
        f"Time of execution: " f"{datetime.now().strftime('%m/%d %H:%M:%S')}"
    )

    t_POI = threading.Thread(target=test_poi)
    t_LPOI = threading.Thread(target=test_plates)
    t_get_cloud_settings = threading.Thread(target=get_cloud_settings)
    t_get_counts = threading.Thread(target=get_counts)
    t_get_trendline_data = threading.Thread(target=get_trendline_data)
    t_get_camera_data = threading.Thread(target=get_camera_data)
    t_get_thumbed = threading.Thread(target=get_thumbed)
    t_get_audit_logs = threading.Thread(target=get_audit_logs)
    t_update_user = threading.Thread(target=update_user)
    t_get_user = threading.Thread(target=get_user)
    t_get_access_groups = threading.Thread(target=get_access_groups)
    t_get_access_users = threading.Thread(target=get_access_users)
    t_change_cards = threading.Thread(target=change_cards)
    t_change_plates = threading.Thread(target=change_plates)
    t_jwt = threading.Thread(target=get_jwt)

    threads = [
        t_get_cloud_settings,
        t_get_counts,
        t_get_trendline_data,
        t_get_camera_data,
        t_get_thumbed,
        t_get_audit_logs,
        t_update_user,
        t_get_user,
        t_get_access_groups,
        t_get_access_users,
        t_change_cards,
        t_change_plates,
        t_jwt,
    ]
    if GPIO:
        # GPIO.output(RUN_PIN, True)  # Solid light while running
        local_stop_event = threading.Event()
        flash_thread = threading.Thread(
            target=work_led, args=(RUN_PIN, local_stop_event, 0.25)
        )
        flash_thread.start()
    start_time = time.time()
    try:
        t_POI.start()
        log.info(
            "%sStarting thread%s%s at time %s.",
            Fore.LIGHTYELLOW_EX,
            Style.RESET_ALL,
            t_POI.name,
            str(datetime.now().strftime("%H:%M:%S")),
        )
        time.sleep(1)
    except ConnectionError:
        log.warning("NewConnectionError caught.")

    t_LPOI.start()
    log.info(
        "%sStarting thread%s%s at time %s.",
        Fore.LIGHTYELLOW_EX,
        Style.RESET_ALL,
        t_LPOI.name,
        str(datetime.now().strftime("%H:%M:%S")),
    )
    time.sleep(1)

    run_thread_with_rate_limit(threads)
    t_POI.join()
    t_LPOI.join()
    # get_user()
    end_time = time.time()
    elapsed = end_time - start_time

    log_execution()

    if GPIO:
        GPIO.output(RUN_PIN, False)

    PASSED = 24 - len(FAILED_ENDPOINTS)
    print_colored_centered(
        elapsed, PASSED, len(FAILED_ENDPOINTS), FAILED_ENDPOINTS
    )

    if GPIO:
        GPIO.cleanup()
