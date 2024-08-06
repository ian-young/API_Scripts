"""
Author: Ian Young
This script will create a POI when given a name and uri to image
"""

# Import essential libraries
import base64
import logging
import threading
import time
from os import getenv
from typing import Any, List

import requests
from dotenv import load_dotenv
from tqdm import tqdm

from QoL.custom_exceptions import APIThrottleException

load_dotenv()  # Load credentials file

# Globally-defined Verkada PoI URL
URL_POI = "https://api.verkada.com/cameras/v1/people/person_of_interest"
URL_LPR = "https://api.verkada.com/cameras/v1/\
analytics/lpr/license_plate_of_interest"

ORG_ID = getenv("")
API_KEY = getenv("")

# Set logger
log = logging.getLogger()
LOG_LEVEL = logging.ERROR
log.setLevel(LOG_LEVEL)
logging.basicConfig(
    level=LOG_LEVEL,
    format="(%(asctime)s.%(msecs)03d) %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Define header and parameters for API requests
HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-api-key": API_KEY,
}

PARAMS = {"org_id": ORG_ID}


##############################################################################
##################################  Misc  ####################################
##############################################################################


class PurgeManager:
    """
    Manages the state of API call count and provides thread-safe methods
    to control and monitor the call limit.

    Attributes:
        call_count (int): The current number of API calls made.
        call_count_lock (threading.Lock): A lock to ensure thread-safe access to call_count.
        call_count_limit (int): The maximum number of API calls allowed.
    """

    def __init__(self, call_count_limit=300):
        """
        Initializes the PurgeManager with a specified call count limit.

        Args:
            call_count_limit (int): The maximum number of API calls allowed.
                                    Defaults to 300.
        """
        self.call_count = 0
        self.call_count_lock = threading.Lock()
        self.call_count_limit = call_count_limit

    def increment_call_count(self):
        """
        Increments the call count by one in a thread-safe manner.

        Returns:
            int: The updated call count after incrementing.
        """
        with self.call_count_lock:
            self.call_count += 1
            return self.call_count

    def should_stop(self):
        """
        Checks if the current call count has reached or exceeded the limit.

        Returns:
            bool: True if the call count has reached or exceeded the limit, False otherwise.
        """
        with self.call_count_lock:
            return self.call_count >= self.call_count_limit

    def reset_call_count(self):
        """
        Resets the call count to zero in a thread-safe manner.
        """
        with self.call_count_lock:
            self.call_count = 0


def clean_list(messy_list: List[Any]) -> List[Any]:
    """
    Removes any None values from error codes

    :param list: The list to be cleaned.
    :type list: list
    :return: A new list with None values removed.
    :rtype: list
    """
    return [value for value in messy_list if value is not None]


##############################################################################
#############################  All Things API  ###############################
##############################################################################


def create_poi(
    poi_name: str, poi_image: str, download: str, manager: PurgeManager
):
    """Will create a person of interest with a given URL to an image or path
    to a file

    :param name: Name of the person of interest to create
    :type name: str
    :param image: The image url to download and use.
    :type image: str
    :param download: Determines whether or not a download is required. Expects
    'y' or 'n'
    :type download: str
    :param manager: The API Throttle manager to prevent hitting the API limit.
    :type manager: PurgeManager
    """
    file_content = None  # Pre-define

    while manager.should_stop():
        log.info("Call limit reached., waiting 1 second.")
        time.sleep(1)
        manager.reset_call_count()

    if download == "y":
        # Download the JPG file from the URL
        img_response = requests.get(poi_image, timeout=5)

        if img_response.status_code == 200:
            # File was successfully downloaded
            file_content = img_response.content
        else:
            # Handle the case where the file download failed
            log.critical("Failed to download the image")
    else:
        file_content = str.encode(poi_image)  # No need to parse the file

    # Convert the binary content to base64
    if file_content:
        base64_image = base64.b64encode(file_content).decode("utf-8")

    # Set payload
    payload = {"label": poi_name, "base64_image": base64_image}

    try:
        response = requests.post(
            URL_POI, json=payload, headers=HEADERS, params=PARAMS, timeout=5
        )

        if response.status_code == 429:
            raise APIThrottleException("API throttled")

        elif response.status_code != 200:
            log.warning(
                "%s: Could not create %s.", response.status_code, poi_name
            )

    except APIThrottleException:
        log.critical("Hit API request rate limit of 500/min")


def create_plate(lpoi_name: str, plate_number: str, manager: PurgeManager):
    """
    Create a LPoI with a given name and plate

    :param plate_name: The name of the license plate to identify what it is.
    :type plate_name: str
    :param plate_number: The value found on the license plate itself.
    :type plate_number: str
    :param manager: The API Throttle manager to prevent hitting the API limit.
    :type manager: PurgeManager
    """
    payload = {"description": lpoi_name, "license_plate": plate_number}

    while manager.should_stop():
        log.info("Call limit reached, waiting for 1 second.")
        time.sleep(1)
        manager.reset_call_count()

    try:
        response = requests.post(
            URL_LPR, json=payload, headers=HEADERS, params=PARAMS, timeout=5
        )

        if response.status_code == 429:
            raise APIThrottleException("API throttled")
        elif response.status_code != 200:
            log.warning(
                "%s Could not create %s.", response.status_code, lpoi_name
            )
            log.warning("Response content: %s", response.status_code)

    except APIThrottleException:
        log.critical("Hit API request rate limit of 500/min")


# Check if the code is being ran directly or imported
if __name__ == "__main__":
    AMOUNT = 40
    progress_bar = tqdm(total=AMOUNT * 2, desc="Creating trash")

    IMAGE = "https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fi.\
pinimg.com%2F736x%2F87%2Fea%2F33%2F87ea336233db8ad468405db8f94da050--human-\
faces-photos-of.jpg&f=1&nofb=1&ipt=6af7ecf6cd0e15496e7197f3b6cb1527beaa8718\
c58609d4feca744209047e57&ipo=images"
    purge_manager = PurgeManager(call_count_limit=100)

    start_time = time.time()
    threads = []
    for i in range(AMOUNT):
        name = f"PoI{i}"
        plate = f"PLATE{i}"
        plate_name = f"Plate{i}"

        log.info("Running for %s & %s", name, plate_name)
        thread_poi = threading.Thread(
            target=create_poi,
            args=(
                name,
                IMAGE,
                "y",
                purge_manager,
            ),
        )
        thread_poi.start()
        threads.append(thread_poi)

        thread_lpoi = threading.Thread(
            target=create_plate,
            args=(
                plate_name,
                plate,
                purge_manager,
            ),
        )
        thread_lpoi.start()
        progress_bar.update(1)

    for thread in threads:
        thread.join()
        progress_bar.update(1)

    progress_bar.close()

    end_time = time.time()
    elapsed_time = end_time - start_time
    log.info("Time to complete: %.2f", elapsed_time)

    print("\nComplete")
