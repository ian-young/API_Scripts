#!/usr/bin/env python
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
from dataclasses import dataclass
from datetime import datetime, timedelta
from os import getenv
from typing import List

import requests
from colorama import Fore, Style, init
from dotenv import load_dotenv

from tools.rate_limit import run_thread_with_rate_limit
from tools.api_endpoints import (
    GET_ALL_POI,
    GET_ALL_LPOI,
    GET_CB,
    GET_PEP_VEH_COUNTS,
    GET_TREND_DATA,
    GET_LATEST_THUMB_IMG,
    GET_STREAM_TOKEN,
    GET_AUDIT_LOGS,
    GET_USER,
    GET_ALL_AC_GROUPS,
    GET_ALL_AC_USRS,
    ADD_CARD_TO_AC_USR,
    ADD_AC_USR_PLATE,
)

# Set log file path & working directory
WORKING_DIRECTORY = "/usr/src/app/data"
log_file_path = f"{WORKING_DIRECTORY}/endpoint_data.log"

# Set logger
log = logging.getLogger()
log.setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
    handlers=[logging.FileHandler(log_file_path), logging.StreamHandler()],
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

try:
    from RPi import GPIO  # type: ignore

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

init(autoreset=True)  # Initialize colorama

load_dotenv()

# Set general testing variables
ORG_ID = getenv("slc_id")  # Org ID
API_KEY = getenv("slc_key")  # API key
STREAM_API_KEY = getenv("slc_stream_key")  # API key with streaming permissions
CAMERA_ID = getenv("slc_camera_id")  # Device ID of camera
TEST_USER = getenv("slc_test_user")  # Command User ID
TEST_USER_CRED = getenv(
    "slc_test_user_cred"
)  # Command user to test AC changes
CARD_ID = getenv("slc_card_id")  # Card ID to manipulate
PLATE = getenv("slc_plate")  # AC plate cred to manipulate

GENERAL_HEADER = {"accept": "application/json", "x-api-key": API_KEY}

FAILED_ENDPOINTS_LOCK = threading.Lock()
MAX_RETRIES = 5  # How many times the program should retry on 429
RETRY_DELAY = 0.25  # Seconds to wait
RETRY_COUNT_LOCK = threading.Lock()


##############################################################################
##################################  Misc  ####################################
##############################################################################


@dataclass
class EndpointData:
    """
    Dataclass representing the data related to API endpoint testing.

    This class holds information about failed API endpoints and the number
    of retry attempts made for those endpoints.

    Attributes:
        failed_endpoints (List[str]): A list of endpoints that have
            failed during testing.
        retry_count (int): The number of retry attempts made for the
            failed endpoints.
    """

    failed_endpoints: List[str]
    retry_count: int


def print_colored_centered(
    runtime: float,
    tests_passed: int,
    failed: int,
    failed_modules: List[str],
    data: EndpointData,
):
    """
    Formats and prints what modules failed and how long it took for the
    program to complete all the tests.

    :param runtime: The time it took for the program to complete.
    :type runtime: float
    :param passed: How many modules passed their tests.
    :type passed: int
    :param failed: How many modules failed their tests.
    :type failed: int
    :param failed_modules: The name of the modules that failed their tests.
    :type failed_modules: list
    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """
    rthread = threading.Thread(
        target=flash_led, args=(RETRY_PIN, data.retry_count)
    )
    fthread = threading.Thread(target=flash_led, args=(FAIL_PIN, failed))
    sthread = threading.Thread(
        target=flash_led, args=(SUCCESS_PIN, tests_passed)
    )

    terminal_width, _ = shutil.get_terminal_size()
    short_time = round(runtime, 2)

    # text1 = f"{Fore.CYAN} short test summary info "
    text2_fail = (
        f"{Fore.RED} {failed} failed, {Fore.GREEN}{tests_passed} "
        f"passed{Fore.RED} in {short_time}s "
    )
    text2_pass = f"{Fore.GREEN} {tests_passed} passed in " f"{short_time}s "
    text2_fail_retry = (
        f"{Fore.RED} {failed} failed, {Fore.GREEN}"
        f"{tests_passed}passed{Fore.RED},{Fore.YELLOW} {data.retry_count} "
        f"retries {Fore.RED} in {short_time}s "
    )
    text2_pass_retry = (
        f"{Fore.GREEN} {tests_passed} passed,{Fore.YELLOW} "
        f"{data.retry_count} retries{Fore.GREEN} in {short_time}s "
    )

    # Print the padded and colored text with "=" characters on both sides
    # An extra line that can be printed if running in live terminal
    # print(f"{Fore.CYAN}{text1:=^{terminal_width+5}}")

    if failed > 0:
        for module in failed_modules:
            print(f"{Fore.RED}FAILED {Style.RESET_ALL}{module}")

        if data.retry_count > 0:
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
        if data.retry_count > 0:
            print(f"{Fore.GREEN}{text2_pass_retry:=^{terminal_width+15}}")
            rthread.start()
            sthread.start()
            rthread.join()
        else:
            print(f"{Fore.GREEN}{text2_pass:=^{terminal_width+5}}")
            sthread.start()

        sthread.join()


def flash_led(pin: int, count: int, speed: float):
    """
    Flashes an LED that is wired into the GPIO board of a raspberry pi

    :param pin: target GPIO pin on the board.
    :type pin: int
    :param count: How many times the LED should flash.
    :type passed: int
    :param speed: How long each flash should last in seconds.
    :type failed: float
    :return: None
    :rtype: None
    """
    for _ in range(count):
        GPIO.output(pin, True)
        time.sleep(speed)
        GPIO.output(pin, False)
        time.sleep(speed)


def work_led(pin: int, stop_event: threading.Event, speed: float):
    """
    Flashes an LED that is wired into the GPIO board of a raspberry pi for
    the duration of work.

    :param pin: target GPIO pin on the board.
    :type pin: int
    :param local_stop_event: Thread-local event to indicate when the program's
    work is done and the LED can stop flashing.
    :type local_stop_event: threading.Event
    :param speed: How long each flash should last in seconds.
    :type failed: float
    :return: None
    :rtype: None
    """
    while not stop_event.is_set():
        GPIO.output(pin, True)
        time.sleep(speed)
        GPIO.output(pin, False)
        time.sleep(speed * 2)


def log_execution(data: EndpointData):
    """
    Writes the final output from running the program into a file to ingest
    later to plot the results.

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    """
    # Save all current entries in the file before changing
    with open(log_file_path, "r", encoding="utf-8") as log_file:
        entries = log_file.readlines()

    # Filter out anything older than 24-hours
    filtered_entries = filter_entries(entries)

    # Overwrite the original file with the filtered entries
    with open("endpoint_data.log", "w", encoding="utf-8") as file:
        file.writelines(filtered_entries)

    # Append the new data to the file
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(
            f"Time of execution: "
            f"{datetime.now().strftime('%m/%d %H:%M:%S')}\n"
        )
        log_file.write(f"Failed endpoints: {len(data.failed_endpoints)}\n")
        log_file.write(f"Retries: {data.retry_count}\n")


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
    return ""


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


def test_poi(data: EndpointData):
    """Serves as a driver function for all POI tests."""
    create_poi(data)
    get_poi(data)
    update_poi(data)
    delete_poi(data)


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
        GET_ALL_POI, headers=GENERAL_HEADER, params=params, timeout=5
    )

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        if persons_of_interest := data.get("persons_of_interest", []):
            return persons_of_interest[0].get("person_id", "")

        log.warning("No person was found with the label 'test'.")

    return ""


def create_poi(data: EndpointData):
    """
    Creates a PoI to test the responsiveness of the API endpoint.

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info("%sRunning%s create_poi", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    # Download the JPG file from the URL
    img_response = requests.get(
        "https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fi.pinimg\
.com%2F736x%2F87%2Fea%2F33%2F87ea336233db8ad468405db8f94da050--human-faces-\
photos-of.jpg&f=1&nofb=1&ipt=6af7ecf6cd0e15496e7197f3b6cb1527beaa8718c58609d4\
feca744209047e57&ipo=images",
        timeout=5,
    )

    if img_response.status_code == 200:
        run_creation(img_response, data)
    else:
        # Handle the case where the file download failed
        log.critical("Failed to download the image")


def run_creation(img_response, data):
    """
    Sends a POST request to create a point of interest using an image.

    This function takes an image response and a data object, converts the
    image to base64, and attempts to send a request to create a point of
    interest. It handles retries in case of rate limiting and logs the
    response status.

    Args:
        img_response: The response object containing the image data.
        data: An object to store information about failed endpoints and
            retry counts.

    Returns:
        None

    Raises:
        None

    Examples:
        run_creation(image_response, endpoint_data)
    """

    # File was successfully downloaded
    file_content = img_response.content

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
            GET_ALL_POI,
            json=payload,
            headers=headers,
            params=params,
            timeout=5,
        )

        if response.status_code != 429:
            break

        log.info("create_poi retrying in %ss. Response: 429", RETRY_DELAY)

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("create_poi response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(f"create_poi: {response.status_code}")


def get_poi(data: EndpointData):
    """
    Looks to see if it can get a list of PoIs

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info("%sRunning%s get_poi", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    params = {"org_id": ORG_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            GET_ALL_POI, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info("get_poi retrying in %ds. Response: 429", data.retry_count)

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("get_poi response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(f"get_poi: {response.status_code}")


def update_poi(data: EndpointData):
    """
    Tests the patch requests for the people endpoint

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

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
            GET_ALL_POI,
            json=payload,
            headers=headers,
            params=params,
            timeout=5,
        )

        if response.status_code != 429:
            break

        log.info("update_poi retrying in %ds. Response: 429", RETRY_DELAY)

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("update_poi response received: %d", response.status_code)

    if response.status_code == 400:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"get_person_id: {response.status_code}"
            )
    elif response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(f"update_poi: {response.status_code}")


def delete_poi(data: EndpointData):
    """
    Tests the delete request for the people endpoint

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info("%sRunning%s delete_poi", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    headers = {"accept": "application/json", "x-api-key": API_KEY}

    params = {"org_id": ORG_ID, "person_id": get_person_id()}

    for _ in range(MAX_RETRIES):
        response = requests.delete(
            GET_ALL_POI, headers=headers, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info("delete_poi retrying in %ds. Response: 429", RETRY_DELAY)

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("delete_poi response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(f"delete_poi: {response.status_code}")


##############################################################################
#################################  Test LPoI  ################################
##############################################################################


def test_plates(data: EndpointData):
    """Serves as a driver function for all LPOI tests."""
    create_plate(data)
    get_plate(data)
    update_plate(data)
    delete_plate(data)


def create_plate(data: EndpointData):
    """
    Creates a Plate to test the API endpoint

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

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
            GET_ALL_LPOI,
            json=payload,
            headers=headers,
            params=params,
            timeout=5,
        )

        if response.status_code != 429:
            break

        log.info("create_plate retrying in %ds. Response: 429", RETRY_DELAY)

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("create_plate response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"create_plate: {response.status_code}"
            )


def get_plate(data: EndpointData):
    """
    Looks to see if it can get Plates

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info("%sRunning%s get_plate", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    headers = {"accept": "application/json", "x-api-key": API_KEY}

    params = {"org_id": ORG_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            GET_ALL_LPOI, headers=headers, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info("get_plate retrying in %ds. Response: 429", RETRY_DELAY)

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("get_plates response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(f"get_plate: {response.status_code}")


def update_plate(data: EndpointData):
    """
    Tests the patch requests for the Plate endpoint

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

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
            GET_ALL_LPOI,
            json=payload,
            headers=headers,
            params=params,
            timeout=5,
        )

        if response.status_code != 429:
            break

        log.info("update_plate retrying in %ds. Response: 429", RETRY_DELAY)

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("update_plate response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"update_plate: {response.status_code}"
            )


def delete_plate(data: EndpointData):
    """
    Tests the delete request for the Plate endpoint

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info("%sRunning%s delete_plate", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    params = {"org_id": ORG_ID, "license_plate": "t3stpl4te"}

    for _ in range(MAX_RETRIES):
        response = requests.delete(
            GET_ALL_LPOI, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info("delete_plate retrying in %ds. Response: 429", RETRY_DELAY)

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("delete_plate response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"delete_plate: {response.status_code}"
            )


##############################################################################
###############################  Test Cameras  ###############################
##############################################################################


def get_cloud_settings(data: EndpointData):
    """
    Tests to see if it can retrieve cloud backup settings for a camera

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info(
        "%sRunning%s get_cloud_settings", Fore.LIGHTBLACK_EX, Style.RESET_ALL
    )

    params = {"org_id": ORG_ID, "camera_id": CAMERA_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            GET_CB, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info(
            "get_cloud_settings retrying in %ds. Response: 429",
            RETRY_DELAY,
        )

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("get_cloud_settings response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"get_cloud_settings: \
{response.status_code}"
            )


def get_counts(data: EndpointData):
    """
    Tests if it can get object counts from a camera

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info("%sRunning%s get_counts", Fore.LIGHTBLACK_EX, Style.RESET_ALL)
    params = {"org_id": ORG_ID, "camera_id": CAMERA_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            GET_PEP_VEH_COUNTS,
            headers=GENERAL_HEADER,
            params=params,
            timeout=5,
        )

        if response.status_code != 429:
            break

        log.info("get_counts retrying in %ds. Response: 429", RETRY_DELAY)

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("get_counts response received")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(f"get_counts: {response.status_code}")


def get_trendline_data(data: EndpointData):
    """
    Tests if it can get trend counts from a camera

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info(
        "%sRunning%s get_trendline_data", Fore.LIGHTBLACK_EX, Style.RESET_ALL
    )

    params = {"org_id": ORG_ID, "camera_id": CAMERA_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            GET_TREND_DATA, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info(
            "get_trend_line_data retrying in %ds. Response: 429",
            RETRY_DELAY,
        )

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("getTrendLineData response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"get_trendline_data: {response.status_code}"
            )


def get_camera_data(data: EndpointData):
    """
    Tests if it can get camera data on a given camera

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info(
        "%sRunning%s get_camera_data", Fore.LIGHTBLACK_EX, Style.RESET_ALL
    )

    params = {"org_id": ORG_ID, "camera_id": CAMERA_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            GET_TREND_DATA, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info(
            "get_camera_data retrying in %ds\
. Response: 429",
            RETRY_DELAY,
        )

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("get_camera_data response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"get_camera_data: {response.status_code}"
            )


def get_thumbed(data: EndpointData):
    """
    Tests if it can get a thumbnail from a camera

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info("%sRunning%s get_thumbnail", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    params = {
        "org_id": ORG_ID,
        "camera_id": CAMERA_ID,
        "resolution": "low-res",
    }

    for _ in range(MAX_RETRIES):
        response = requests.get(
            GET_LATEST_THUMB_IMG,
            headers=GENERAL_HEADER,
            params=params,
            timeout=5,
        )

        if response.status_code != 429:
            break

        log.info(
            "getThumbnail retrying in %ds. Response: 429",
            RETRY_DELAY,
        )

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("getThumbnail response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"getThumbnail: {response.status_code}"
            )


##############################################################################
#################################  Test Core  ################################
##############################################################################


def get_audit_logs(data: EndpointData):
    """
    Tests the ability to retrieve audit logs

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info("%sRunning%s get_audit_logs", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    params = {"org_id": ORG_ID, "page_size": "1"}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            GET_AUDIT_LOGS, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info(
            "get_audit_logs retrying in %ds. Response: 429",
            RETRY_DELAY,
        )

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

        log.info(
            "get_audit_logsLogs response received: %d", response.status_code
        )

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"get_audit_logs: {response.status_code}"
            )


def update_user(data: EndpointData):
    """
    Tests the ability to update a user

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

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
            GET_USER, json=payload, headers=headers, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info("update_user retrying in %ds. Response: 429", RETRY_DELAY)

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("update_user response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"update_user: {response.status_code}"
            )


def get_user(data: EndpointData):
    """
    Tests the ability to retrieve information on a user

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info("%sRunning%s get_user", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    params = {"user_id": TEST_USER}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            GET_USER, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info("get_user retrying in %ds. Response: 429", RETRY_DELAY)

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("get_user response received: {response.status_code}")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(f"get_user: {response.status_code}")


def get_jwt(data: EndpointData, org_id=ORG_ID, api_key=STREAM_API_KEY):
    """
    Generates a JWT token for the streaming API. This token will be integrated
    inside of a link to grant access to footage.

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: Returns the JWT token to allow access via a link to footage.
    :rtype: str
    """

    log.info("%sRunning%s get_jwt", Fore.LIGHTBLACK_EX, Style.RESET_ALL)

    # Define the request headers
    headers = {"x-api-key": api_key}

    # Set the parameters of the request
    params = {"org_id": org_id, "expiration": 60}

    for _ in range(MAX_RETRIES):

        # Send GET request to get the JWT
        response = requests.get(
            GET_STREAM_TOKEN, headers=headers, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info("get_jwt retrying in %ds. Response: 429", RETRY_DELAY)

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("get_jwt response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(f"get_jwt: {response.status_code}")


##############################################################################
##########################  Test Access Control  #############################
##############################################################################


def get_access_groups(data: EndpointData):
    """
    Tests the ability to get AC Groups

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info(
        "%sRunning%s get_access_groups", Fore.LIGHTBLACK_EX, Style.RESET_ALL
    )

    params = {"org_id": ORG_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            GET_ALL_AC_GROUPS, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info(
            "get_access_groups retrying in %ds. Response: 429", RETRY_DELAY
        )

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("get_access_groups response received")

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"get_access_groups: {response.status_code}"
            )


def get_access_users(data: EndpointData):
    """
    Tests the ability to get AC users

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info(
        "%sRunning%s get_access_users", Fore.LIGHTBLACK_EX, Style.RESET_ALL
    )

    params = {"org_id": ORG_ID}

    for _ in range(MAX_RETRIES):
        response = requests.get(
            GET_ALL_AC_USRS, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if response.status_code != 429:
            break

        log.info(
            "get_access_users retrying in %ds. \
Response: 429",
            RETRY_DELAY,
        )

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info("get_access_users response received: %d", response.status_code)

    if response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"get_access_users: {response.status_code}"
            )


def change_cards(data: EndpointData):
    """
    Tests the ability to change credentials

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

    log.info(
        "%sRunning%s activate_card \
& deactivate_card",
        Fore.LIGHTBLACK_EX,
        Style.RESET_ALL,
    )

    params = {"org_id": ORG_ID, "user_id": TEST_USER_CRED, "card_id": CARD_ID}

    activate_url = f"{ADD_CARD_TO_AC_USR}/activate"
    deactivate_url = f"{ADD_CARD_TO_AC_USR}/deactivate"

    for _ in range(MAX_RETRIES):
        active_response = requests.put(
            activate_url, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if active_response.status_code != 429:
            break

        log.info(
            "activate_card retrying in %ds. \
Response: 429",
            RETRY_DELAY,
        )

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info(
        "activate_card response received: %d", active_response.status_code
    )

    for _ in range(MAX_RETRIES):
        deactivate_response = requests.put(
            deactivate_url, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if deactivate_response.status_code != 429:
            break

        log.info(
            "deactivate_card retrying in %ds. \
Response: 429",
            RETRY_DELAY,
        )

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info(
        "deactivate_card response received: %d",
        deactivate_response.status_code,
    )

    if active_response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"activate_card: \
{active_response.status_code}"
            )

    elif deactivate_response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"deactivate_card: \
{deactivate_response.status_code}"
            )


def change_plates(data: EndpointData):
    """
    Tests the ability to change access plates

    :param data: An instance of EndpointData containing the
        necessary parameters for the reporting process.
    :type data: EndpointData
    :return: None
    :rtype: None
    """

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

    activate_url = f"{ADD_AC_USR_PLATE}/activate"
    deactivate_url = f"{ADD_AC_USR_PLATE}/deactivate"

    for _ in range(MAX_RETRIES):
        active_response = requests.put(
            activate_url, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if active_response.status_code != 429:
            break

        log.info(
            "activatePlate retrying in %ds. \
Response: 429",
            RETRY_DELAY,
        )

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info(
        "activatePlate response received: %d", active_response.status_code
    )

    for _ in range(MAX_RETRIES):
        deactivate_response = requests.put(
            deactivate_url, headers=GENERAL_HEADER, params=params, timeout=5
        )

        if deactivate_response.status_code != 429:
            break

        log.info(
            "deactivatePlate retrying in %ds. \
Response: 429",
            RETRY_DELAY,
        )

        with RETRY_COUNT_LOCK:
            data.retry_count += 1

        time.sleep(RETRY_DELAY)  # Wait for throttle refresh

    log.info(
        "deactivatePlate response received: %d",
        deactivate_response.status_code,
    )

    if active_response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"activatePlate: \
{active_response.status_code}"
            )

    elif deactivate_response.status_code != 200:
        with FAILED_ENDPOINTS_LOCK:
            data.failed_endpoints.append(
                f"deactivatePlate: \
{deactivate_response.status_code}"
            )


##############################################################################
##################################  Main  ####################################
##############################################################################

if __name__ == "__main__":
    print(
        f"Time of execution: " f"{datetime.now().strftime('%m/%d %H:%M:%S')}"
    )

    runtime_data = EndpointData([], 0)

    t_POI = threading.Thread(target=test_poi, args=(runtime_data,))
    t_LPOI = threading.Thread(target=test_plates, args=(runtime_data,))
    t_get_cloud_settings = threading.Thread(
        target=get_cloud_settings, args=(runtime_data,)
    )
    t_get_counts = threading.Thread(target=get_counts, args=(runtime_data,))
    t_get_trendline_data = threading.Thread(
        target=get_trendline_data, args=(runtime_data,)
    )
    t_get_camera_data = threading.Thread(
        target=get_camera_data, args=(runtime_data,)
    )
    t_get_thumbed = threading.Thread(target=get_thumbed, args=(runtime_data,))
    t_get_audit_logs = threading.Thread(
        target=get_audit_logs, args=(runtime_data,)
    )
    t_update_user = threading.Thread(target=update_user, args=(runtime_data,))
    t_get_user = threading.Thread(target=get_user, args=(runtime_data,))
    t_get_access_groups = threading.Thread(
        target=get_access_groups, args=(runtime_data,)
    )
    t_get_access_users = threading.Thread(
        target=get_access_users, args=(runtime_data,)
    )
    t_change_cards = threading.Thread(
        target=change_cards, args=(runtime_data,)
    )
    t_change_plates = threading.Thread(
        target=change_plates, args=(runtime_data,)
    )
    t_jwt = threading.Thread(target=get_jwt, args=(runtime_data,))

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

    run_thread_with_rate_limit(threads, "Reaching out to endpoints")
    t_POI.join()
    t_LPOI.join()
    # get_user()
    end_time = time.time()
    elapsed = end_time - start_time

    log_execution(runtime_data)

    if GPIO:
        GPIO.output(RUN_PIN, False)

    PASSED = 24 - len(runtime_data.failed_endpoints)
    print_colored_centered(
        elapsed,
        PASSED,
        len(runtime_data.failed_endpoints),
        runtime_data.failed_endpoints,
        runtime_data,
    )

    if GPIO:
        GPIO.cleanup()
