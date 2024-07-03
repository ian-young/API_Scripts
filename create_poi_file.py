"""
Author: Ian Young
This script will create a POI when given a name and file path to an image
"""
# Import essential libraries
import logging
import base64
import threading
import time
from os import getenv

import colorama
import requests
from colorama import Fore, Style
from dotenv import load_dotenv

colorama.init(autoreset=True)

load_dotenv()  # Load credentials file

# Set logger
log = logging.getLogger()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Globally-defined Verkada PoI URL
URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"
API_KEY = getenv("")
ORG_ID = getenv("")
IMAGE_PATH = "/Users/ian.young/Pictures/thispersondoesnotexist2.jpg"

# Each file name must be on a new line. File name format is expected to be
# the student's name then .jpg or whatever the format is. The file MUST be
# in the same directory of the script.
PATH_LIST = "test.txt"


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


##############################################################################
################################  API Calls  #################################
##############################################################################


def create_poi(manager, name, path=IMAGE_PATH, org_id=ORG_ID, api_key=API_KEY):
    """
    Will create a person of interest with a given URL to an image or path to
    a file.

    :param name: The label for the person of interest to be created.
    :type name: str
    :param path: Expected to be the name of an image that resides in the same
    directory of the script being ran.
    :type path: str
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: None
    :rtype: None
    """
    file_content = None  # Pre-define

    try:
        with open(path, "rb") as image_file:
            # Read the binary content
            file_content = image_file.read()

    except FileNotFoundError:
        logging.error(
            "%sError:%s The path was not found.", Fore.RED, Style.RESET_ALL
        )

    if file_content is not None:
        log.debug("%sEncoding file...", Fore.LIGHTCYAN_EX)

        # Convert the binary content to base64
        base64_image = base64.b64encode(file_content).decode("utf-8")
        log.debug("%sFile encoded!", Fore.LIGHTGREEN_EX)

        log.debug("%sCalling API endpoint...", Fore.LIGHTCYAN_EX)

        # Set payload
        payload = {"label": name, "base64_image": base64_image}
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": api_key,
        }

        params = {"org_id": org_id}
        while manager.should_stop():
            log.info("Call limit reached, waiting for 1 second.")
            time.sleep(1)
            manager.reset_call_count()

        response = requests.post(
            URL, json=payload, headers=headers, params=params, timeout=5
        )

        if response.status_code == 200:
            log.info("%s successfully created.", name)

        elif response.status_code == 504:
            log.warning("%s Request timed out.", Fore.LIGHTRED_EX)

        elif response.status_code == 400:
            log.error("%sFailed 400. Check image quality.", Fore.RED)

        else:
            log.error(
                "%sFailed:%s %s",
                Fore.RED,
                Style.RESET_ALL,
                response.status_code,
            )


##############################################################################
##################################  Main  ####################################
##############################################################################


# Check if the code is being ran directly or imported
if __name__ == "__main__":
    threads = []
    purge_manager = PurgeManager(call_count_limit=300)

    try:
        log.debug("%sReading file...", Fore.LIGHTCYAN_EX)
        file = open(PATH_LIST, "r", encoding="utf-8")
        lines = file.readlines()

        for line in lines:
            log.debug("%s %s", {line.split(".")[0]}, {line.strip()})
            new_thread = threading.Thread(
                target=create_poi,
                args=(
                    purge_manager,
                    line.split(".")[0],
                    line.strip(),
                ),
            )

            threads.append(new_thread)
            new_thread.start()

        for thread in threads:
            thread.join()

    except FileNotFoundError:
        print(f"{Fore.RED}File {PATH_LIST} not found.")
