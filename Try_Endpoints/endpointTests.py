#!/usr/bin/env python
# Author: Ian Young
# Purpose: Test Verkada API endpoints.
# This script is to be ran using the pip module pytest
# Anything that starts with test will be ran by pytest
# The script only looks for a 200 response code.

import requests
import base64
import docker
import colorama
from colorama import Fore, Style
import threading
import shutil
import time
from datetime import datetime, timedelta
import logging
import re

# Set log file path
log_file_path = "/usr/src/app/endpoint_data.log"

# Set logger
log = logging.getLogger()
log.setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

try:
    import RPi.GPIO as GPIO  # type: ignore

    retry_pin = 11
    fail_pin = 13
    run_pin = 7
    success_pin = 15

    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(run_pin, GPIO.OUT)
        GPIO.setup(retry_pin, GPIO.OUT)
        GPIO.setup(fail_pin, GPIO.OUT)
        if success_pin:
            GPIO.setup(success_pin, GPIO.OUT)
    except RuntimeError:
        GPIO = None
        log.debug("GPIO Runtime error")
except ImportError:
    GPIO = None
    log.debug("RPi.GPIO is not availbale. Running on a non-Pi platform")

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

# Set general testing variables
ORG_ID = docker.slc_id  # Org ID
API_KEY = docker.slc_key  # API key
STREAM_API_KEY = docker.slc_stream_key  # API key with streaming permissions
CAMERA_ID = docker.slc_camera_id  # Device ID of camera
TEST_USER = docker.slc_test_user  # Command User ID
TEST_USER_CRED = docker.slc_test_user_cred  # Command user to test AC changes
CARD_ID = docker.slc_card_id  # Card ID to manipulate
PLATE = docker.slc_plate  # AC plate cred to manipulate

GENERAL_HEADER = {
    'accept': 'application/json',
    'x-api-key': API_KEY
}

FAILED_ENDPOINTS = []
FAILED_ENDPOINTS_LOCK = threading.Lock()
MAX_RETRIES = 5  # How many times the program should retry on 429
RETRY_DELAY = 0.25   # Seconds to wait
RETRY_COUNT = 0
RETRY_COUNT_LOCK = threading.Lock()


##############################################################################
                                    # Misc #
##############################################################################


class RateLimiter:
    def __init__(self, rate_limit, max_events_per_sec=10, pacing=1):
        """
        Initilization of the rate limiter.

        :param rate_limit: The value of how many threads may be made each sec.
        :type rate_limit: int
        :param max_events_per_sec: Maximum events allowed per second.
        :type: int
        :return: None
        :rtype: None
        """
        self.rate_limit = rate_limit
        self.lock = threading.Lock()  # Local lock to prevent race conditions
        self.max_events_per_sec = max_events_per_sec
        self.pacing = pacing

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
            elapsed_time = current_time - self.start_time

            # Check if it's been less than 1sec and less than 10 events have
            # been made.
            if elapsed_time < self.pacing / self.rate_limit \
                    and self.event_count < self.max_events_per_sec:
                self.event_count += 1
                return True

            # Check if it is the first wave of events
            elif elapsed_time >= self.pacing / self.rate_limit:
                self.start_time = current_time
                self.event_count = 2
                return True

            else:
                # Calculate the time left before next wave
                remaining_time = self.pacing - \
                    (current_time - self.start_time)
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
    limiter = RateLimiter(rate_limit=rate_limit,)

    def run_thread(thread):
        with threading.Lock():
            limiter.acquire()
            log.info(f"{Fore.LIGHTYELLOW_EX}Starting thread{Style.RESET_ALL} \
{thread.name} at time {datetime.now().strftime('%H:%M:%S')}")
            thread.start()

    for thread in threads:
        run_thread(thread)

    for thread in threads:
        thread.join()


def print_colored_centered(time, passed, failed, failed_modules):
    """
    Formats and prints what modules failed and how long it took for the
    program to complete all the tests.

    :param time: The time it took for the program to complete.
    :type time: int
    :param passed: How many modules passed their tests.
    :type passed: int
    :param failed: How many modules failed their tests.
    :type failed: int
    :param failed_modules: The name of the modules that failed their tests.
    :type failed_modules: list
    :return: None
    :rtype: None
    """
    global RETRY_COUNT
    if GPIO:
        rthread = threading.Thread(
            target=flashLED, args=(retry_pin, RETRY_COUNT, 0.5))
        fthread = threading.Thread(target=flashLED, args=(fail_pin, failed, 1))
        sthread = threading.Thread(
            target=flashLED, args=(success_pin, passed, 0.1))
        csthread = threading.Thread(target=flashLED, args=(success_pin, 1, 5))

    terminal_width, _ = shutil.get_terminal_size()
    short_time = round(time, 2)

    text1 = f"{Fore.CYAN} short test summary info "
    text2_fail = f"{Fore.RED} {failed} failed, {Fore.GREEN}{passed} \
passed{Fore.RED} in {short_time}s "
    text2_pass = f"{Fore.GREEN} {passed} passed in \
{short_time}s "
    text2_fail_retry = f"{Fore.RED} {failed} failed, {Fore.GREEN}{passed} \
passed{Fore.RED},{Fore.YELLOW} {RETRY_COUNT} retries{Fore.RED} in \
{short_time}s "
    text2_pass_retry = f"{Fore.GREEN} {passed} passed,{Fore.YELLOW} \
{RETRY_COUNT} retries{Fore.GREEN} in {short_time}s "

    # Print the padded and colored text with "=" characters on both sides
    # An extra line that can be printed if running in live terminal
    # print(f"{Fore.CYAN}{text1:=^{terminal_width+5}}")

    if failed > 0:
        for module in failed_modules:
            print(f"{Fore.RED}FAILED {Style.RESET_ALL}{module}")

        if RETRY_COUNT > 0:
            print(f"{Fore.RED}{text2_fail_retry:=^{terminal_width+25}}")
            if GPIO:
                rthread.start()
                fthread.start()
                sthread.start()
                sthread.join()
                rthread.join()
                fthread.join()
        else:
            print(f"{Fore.RED}{text2_fail:=^{terminal_width+15}}")
            if GPIO:
                sthread.start()
                fthread.start()
                sthread.join()
                fthread.join()
    else:
        if RETRY_COUNT > 0:
            print(f"{Fore.GREEN}{text2_pass_retry:=^{terminal_width+15}}")
            if GPIO:
                rthread.start()
                csthread.start()
                rthread.join()
                csthread.join()
        else:
            print(f"{Fore.GREEN}{text2_pass:=^{terminal_width+5}}")
            if GPIO:
                flashLED(success_pin, 1, 1)


def flashLED(pin, count, speed):
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


def workLED(pin, local_stop_event, speed):
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


def log_execution():
    """
    Writes the final output from running the program into a file to ingest
    later to plot the results.
    """
    # Save all current entries in the file before changing
    with open(log_file_path, 'r') as log_file:
        entries = log_file.readlines()

    # Filter out anything older than 24-hours
    filtered_entries = filter_entries(entries)

    # Overwrite the original file with the filtered entries
    with open("endpoint_data.log", "w") as file:
        file.writelines(filtered_entries)

    # Append the new data to the file
    with open(log_file_path, 'a') as log_file:
        log_file.write(
            f"Time of execution: "
            f"{datetime.now().strftime('%m/%d %H:%M:%S')}\n")
        log_file.write(f"Failed endpoints: {len(FAILED_ENDPOINTS)}\n")
        log_file.write(f"Retries: {RETRY_COUNT}\n")


def parse_entry(entry):
    # Use regular expression to extract the time string in the entry
    time_match = re.search(r"(\d{2}/\d{2} \d{2}:\d{2}:\d{2})", entry)
    if time_match:
        time_str = time_match.group(1)
        # Set the year to the current year
        current_year = datetime.now().year
        return datetime.strptime(f"{current_year} {time_str}", "%Y %m/%d %H:%M:%S")


def filter_entries(entries):
    filtered_entries = []
    current_time = datetime.now()

    include_entry = False

    for entry in entries:
        execution_time = parse_entry(entry)
        if execution_time:
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
                            #  Test PoI  #
##############################################################################


def testPOI():
    createPOI()
    getPOI()
    updatePOI()
    deletePOI()


def getPersonID():
    """
    Accepts a string as a search value and returns the person id
 associated with it

    :return: The person id for the search value hard-coded into label.
    :rtype: str
    """
    # Define query parameters for the request
    params = {
        'org_id': ORG_ID,
        'label': 'test'
    }

    # Send a GET request to search for persons of interest
    response = requests.get(URL_PEOPLE, headers=GENERAL_HEADER, params=params)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Extract the list of persons of interest
        persons_of_interest = data.get('persons_of_interest', [])

        if persons_of_interest:
            # Extract the person_id from the first (and only) result
            person_id = persons_of_interest[0].get('person_id')
            return person_id
            # print(f"Person ID for label '{label_to_search}': {person_id}")
        else:
            log.warning(f"No person was found with the label 'test'.")


def createPOI():
    """
    Creates a PoI to test the responsiveness of the API endpoint.

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} createPoI")

    file_content = None  # Pre-define

    # Download the JPG file from the URL
    img_response = requests.get(
        'https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fi.pinimg\
.com%2F736x%2F87%2Fea%2F33%2F87ea336233db8ad468405db8f94da050--human-faces-\
photos-of.jpg&f=1&nofb=1&ipt=6af7ecf6cd0e15496e7197f3b6cb1527beaa8718c58609d4\
feca744209047e57&ipo=images')

    if img_response.status_code == 200:
        # File was successfully downloaded
        file_content = img_response.content
    else:
        # Handle the case where the file download failed
        log.critical("Failed to download the image")

    # Convert the binary content to base64
    base64_image = base64.b64encode(file_content).decode('utf-8')

    # Set payload
    payload = {
        "label": 'test',
        "base64_image": base64_image
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY
    }

    params = {
        "org_id": ORG_ID
    }

    for _ in range(MAX_RETRIES):
        response = requests.post(
            URL_PEOPLE, json=payload, headers=headers, params=params)

        if response.status_code == 429:
            log.info(f"createPoI retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"createPoI response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"CreatePoI: {response.status_code}")


def getPOI():
    """
    Looks to see if it can get a list of PoIs

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} getPoI")

    params = {
        "org_id": ORG_ID
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_PEOPLE, headers=GENERAL_HEADER, params=params)

        if response.status_code == 429:
            log.info(f"getPoI retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"getPoI response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getPoI: {response.status_code}")


def updatePOI():
    """
    Tests the patch requests for the people endpoint

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} updatePoI")

    payload = {"label": 'Test'}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY
    }

    # Define query parameters for the request
    params = {
        'org_id': ORG_ID,
        'person_id': getPersonID()
    }

    for _ in range(MAX_RETRIES):
        response = requests.patch(
            URL_PEOPLE, json=payload, headers=headers, params=params)

        if response.status_code == 429:
            log.info(f"updatePoI retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"updatePoI response received: {response.status_code}")

    if response.status_code == 400:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getPersonID: {response.status_code}")
    elif response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"updatePoI: {response.status_code}")


def deletePOI():
    """
    Tests the delete request for the people endpoint

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} deletePoI")

    headers = {
        "accept": "application/json",
        "x-api-key": API_KEY
    }

    params = {
        "org_id": ORG_ID,
        "person_id": getPersonID()
    }

    for _ in range(MAX_RETRIES):
        response = requests.delete(URL_PEOPLE, headers=headers, params=params)

        if response.status_code == 429:
            log.info(f"deletePoI retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"deletePoI response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"deletePoI: {response.status_code}")


##############################################################################
                            #  Test LPoI  #
##############################################################################


def testLPOI():
    createPlate()
    getPlate()
    updatePlate()
    deletePlate()


def createPlate():
    """
    Creates a Plate to test the API endpoint

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} createPlate")

    # Set payload
    payload = {
        "description": 'test',
        "license_plate": 't3stpl4te'
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY
    }

    params = {
        "org_id": ORG_ID
    }

    for _ in range(MAX_RETRIES):
        response = requests.post(
            URL_PLATE, json=payload, headers=headers, params=params)

        if response.status_code == 429:
            log.info(f"createPlate retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"createPlate response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"createPlate: {response.status_code}")


def getPlate():
    """
    Looks to see if it can get Plates

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} getPlate")

    headers = {
        "accept": "application/json",
        "x-api-key": API_KEY
    }

    params = {
        "org_id": ORG_ID
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(URL_PLATE, headers=headers, params=params)

        if response.status_code == 429:
            log.info(f"getPlate retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"getPlates response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getPlate: {response.status_code}")


def updatePlate():
    """
    Tests the patch requests for the Plate endpoint

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} updatePlate")

    payload = {"description": 'Test'}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY
    }

    # Define query parameters for the request
    params = {
        'org_id': ORG_ID,
        'license_plate': "t3stpl4te"
    }

    for _ in range(MAX_RETRIES):
        response = requests.patch(
            URL_PLATE, json=payload, headers=headers, params=params)

        if response.status_code == 429:
            log.info(f"updatePlate retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"updatePlate response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"updatePlate: {response.status_code}")


def deletePlate():
    """
    Tests the delete request for the Plate endpoint

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} deletePlate")

    params = {
        "org_id": ORG_ID,
        'license_plate': "t3stpl4te"
    }

    for _ in range(MAX_RETRIES):
        response = requests.delete(
            URL_PLATE, headers=GENERAL_HEADER, params=params)

        if response.status_code == 429:
            log.info(f"deletePlate retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"deletePlate response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"deletePlate: {response.status_code}")


##############################################################################
                            # Test Cameras #
##############################################################################


def getCloudSettings():
    """
    Tests to see if it can retrieve cloud backup settings for a camera

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} getCloudSettings")

    params = {
        'org_id': ORG_ID,
        'camera_id': CAMERA_ID
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_CLOUD, headers=GENERAL_HEADER, params=params)

        if response.status_code == 429:
            log.info(f"getCloudSettings retrying in {RETRY_DELAY}s.\
 Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"getCloudSettings response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getCloudSettings: \
{response.status_code}")


def getCounts():
    """
    Tests if it can get object counts from a camera

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} getCounts")
    params = {
        'org_id': ORG_ID,
        'camera_id': CAMERA_ID
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(URL_OBJ, headers=GENERAL_HEADER, params=params)

        if response.status_code == 429:
            log.info(f"getCounts retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("getCounts response received")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getCounts: {response.status_code}")


def getTrends():
    """
    Tests if it can get trend counts from a camera

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} getTrendLineData")

    params = {
        'org_id': ORG_ID,
        'camera_id': CAMERA_ID
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_OCCUPANCY, headers=GENERAL_HEADER, params=params)

        if response.status_code == 429:
            log.info(f"getTrendLineData retrying in {RETRY_DELAY}s.\
 Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"getTrendLineData response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getTrends: {response.status_code}")


def getCameraData():
    """
    Tests if it can get camera data on a given camera

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} getCameraData")

    params = {
        'org_id': ORG_ID,
        'camera_id': CAMERA_ID
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_OCCUPANCY, headers=GENERAL_HEADER, params=params)

        if response.status_code == 429:
            log.info(f"getCameraData retrying in {RETRY_DELAY}s\
. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"getCameraData response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getCameraData: {response.status_code}")


def getThumbed():
    """
    Tests if it can get a thumbnail from a camera

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} getThumbnail")

    params = {
        'org_id': ORG_ID,
        'camera_id': CAMERA_ID,
        'resolution': 'low-res'
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_FOOTAGE, headers=GENERAL_HEADER, params=params)

        if response.status_code == 429:
            log.info(f"getThumbnail retrying in {RETRY_DELAY}s.\
 Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"getThumbnail response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getThumbnail: {response.status_code}")


##############################################################################
                                # Test Core #
##############################################################################


def getAudit():
    """
    Tests the ability to retrieve audit logs

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} getAuditLogs")

    params = {
        'org_id': ORG_ID,
        'page_size': '1'
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(URL_AUDIT, headers=GENERAL_HEADER,
                                params=params)

        if response.status_code == 429:
            log.info(f"getAuditLogs retrying in {RETRY_DELAY}s.\
 Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"getAuditLogs response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getAudit: {response.status_code}")


def updateUser():
    """
    Tests the ability to update a user

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} updateUser")

    payload = {
        'active': False
    }

    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'x-api-key': API_KEY
    }

    params = {
        'org_id': ORG_ID,
        'user_id': TEST_USER
    }

    for _ in range(MAX_RETRIES):
        response = requests.put(URL_CORE, json=payload,
                                headers=headers, params=params)

        if response.status_code == 429:
            log.info(f"updateUser retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"updateUser response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"updateUser: {response.status_code}")


def getUser():
    """
    Tests the ability to retrieve information on a user

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} getUser")

    params = {
        'user_id': TEST_USER
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(URL_CORE, headers=GENERAL_HEADER,
                                params=params)

        if response.status_code == 429:
            log.info(f"getUser retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"getUser response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getUser: {response.status_code}")


def getJWT(org_id=ORG_ID, api_key=STREAM_API_KEY):
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

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} getJWT")

    # Define the request headers
    headers = {
        'x-api-key': api_key
    }

    # Set the parameters of the request
    params = {
        'org_id': org_id,
        'expiration': 60
    }

    for _ in range(MAX_RETRIES):

        # Send GET request to get the JWT
        response = requests.get(URL_TOKEN, headers=headers, params=params)

        if response.status_code == 429:
            log.info(f"getJWT retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"getJWT response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getJWT: {response.status_code}")


##############################################################################
                            # Test Access Control #
##############################################################################


def getGroups():
    """
    Tests the ability to get AC Groups

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} getAccessGroups")

    params = {
        'org_id': ORG_ID
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_AC_GROUPS, headers=GENERAL_HEADER, params=params)

        if response.status_code == 429:
            log.info(f"getGroups retrying in {RETRY_DELAY}s. Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info("getGroups response received")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getGroups: {response.status_code}")


def getACUsers():
    """
    Tests the ability to get AC users

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} getAccessUsers")

    params = {
        'org_id': ORG_ID
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(
            URL_AC_USERS, headers=GENERAL_HEADER, params=params)

        if response.status_code == 429:
            log.info(f"getAccessUsers retrying in {RETRY_DELAY}s.\
 Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"getAccessUsers response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"getACUsers: {response.status_code}")


def changeCards():
    """
    Tests the ability to change credentials

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} activateCard\
 & deactivateCard")

    params = {
        'org_id': ORG_ID,
        'user_id': TEST_USER_CRED,
        'card_id': CARD_ID
    }

    activate_url = URL_AC_CRED + '/activate'
    deactivate_url = URL_AC_CRED + '/deactivate'

    for _ in range(MAX_RETRIES):
        active_response = requests.put(
            activate_url, headers=GENERAL_HEADER, params=params)

        if active_response.status_code == 429:
            log.info(f"activateCard retrying in {RETRY_DELAY}s.\
 Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"activateCard response received: {active_response.status_code}")

    for _ in range(MAX_RETRIES):
        deactive_response = requests.put(
            deactivate_url, headers=GENERAL_HEADER, params=params)

        if deactive_response.status_code == 429:
            log.info(f"deactivateCard retrying in {RETRY_DELAY}s.\
 Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"deactivateCard response received: \
{deactive_response.status_code}")

    if active_response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"activateCard: \
{active_response.status_code}")

    elif deactive_response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"deactivateCard: \
{deactive_response.status_code}")


def changePlates():
    """
    Tests the ability to change access plates

    :return: None
    :rtype: None
    """
    global FAILED_ENDPOINTS
    global RETRY_COUNT

    log.info(f"{Fore.LIGHTBLACK_EX}Running{Style.RESET_ALL} activatePlate\
 & deactivatePlate")

    params = {
        'org_id': ORG_ID,
        'user_id': TEST_USER_CRED,
        'license_plate_number': PLATE
    }

    activate_url = URL_AC_PLATE + '/activate'
    deactivate_url = URL_AC_PLATE + '/deactivate'

    for _ in range(MAX_RETRIES):
        active_response = requests.put(
            activate_url, headers=GENERAL_HEADER, params=params)

        if active_response.status_code == 429:
            log.info(f"activatePlate retrying in {RETRY_DELAY}s.\
 Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"activatePlate response received: \
{active_response.status_code}")

    for _ in range(MAX_RETRIES):
        deactive_response = requests.put(
            deactivate_url, headers=GENERAL_HEADER, params=params)

        if deactive_response.status_code == 429:
            log.info(f"deactivatePlate retrying in {RETRY_DELAY}s.\
 Response: 429")

            with RETRY_COUNT_LOCK:
                RETRY_COUNT += 1

            time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        else:
            break

    log.info(f"deactivatePlate response received: \
{deactive_response.status_code}")

    if active_response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"activatePlate: \
{active_response.status_code}")

    elif deactive_response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            FAILED_ENDPOINTS.append(f"deactivatePlate: \
{deactive_response.status_code}")


##############################################################################
                                # Main #
##############################################################################

if __name__ == '__main__':
    print(f"Time of execution: "
          f"{datetime.now().strftime('%m/%d %H:%M:%S')}")

    t_POI = threading.Thread(target=testPOI)
    t_LPOI = threading.Thread(target=testLPOI)
    t_getCloudSettings = threading.Thread(target=getCloudSettings)
    t_getCounts = threading.Thread(target=getCounts)
    t_getTrends = threading.Thread(target=getTrends)
    t_getCameraData = threading.Thread(target=getCameraData)
    t_getThumbed = threading.Thread(target=getThumbed)
    t_getAudit = threading.Thread(target=getAudit)
    t_updateUser = threading.Thread(target=updateUser)
    t_getUser = threading.Thread(target=getUser)
    t_getGroups = threading.Thread(target=getGroups)
    t_getACUsers = threading.Thread(target=getACUsers)
    t_changeCards = threading.Thread(target=changeCards)
    t_changePlates = threading.Thread(target=changePlates)
    t_jwt = threading.Thread(target=getJWT)

    threads = [t_getCloudSettings, t_getCounts, t_getTrends,
               t_getCameraData, t_getThumbed, t_getAudit, t_updateUser,
               t_getUser, t_getGroups, t_getACUsers, t_changeCards,
               t_changePlates, t_jwt]
    if GPIO:
        # GPIO.output(run_pin, True)  # Solid light while running
        local_stop_event = threading.Event()
        flash_thread = threading.Thread(target=workLED,
                                        args=(run_pin, local_stop_event, 0.25))
        flash_thread.start()
    start_time = time.time()
    try:
        t_POI.start()
        log.info(f"{Fore.LIGHTYELLOW_EX}Starting thread{Style.RESET_ALL} \
{t_POI.name} at time {datetime.now().strftime('%H:%M:%S')}")
        time.sleep(1)
    except ConnectionError:
        log.warning("NewConnectionError caught.")

    t_LPOI.start()
    log.info(f"{Fore.LIGHTYELLOW_EX}Starting thread{Style.RESET_ALL} \
{t_LPOI.name} at time {datetime.now().strftime('%H:%M:%S')}")
    time.sleep(1)

    run_thread_with_rate_limit(threads)
    t_POI.join()
    t_LPOI.join()
    # getUser()
    end_time = time.time()
    elapsed = end_time - start_time

    log_execution()

    if GPIO:
        # GPIO.output(run_pin, False)  # Solid light while running
        local_stop_event.set()
        flash_thread.join()

    passed = 24 - len(FAILED_ENDPOINTS)
    print_colored_centered(elapsed, passed, len(
        FAILED_ENDPOINTS), FAILED_ENDPOINTS)
    if GPIO:
        GPIO.cleanup()
