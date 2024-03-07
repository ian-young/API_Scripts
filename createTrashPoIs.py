# Author: Ian Young
# This script will create a POI when given a name and uri to image

import base64
import colorama
import datetime
import logging
import random
import requests
import string
import threading
import time

from os import getenv
from colorama import Fore, Style
from dotenv import load_dotenv

# Set style to reset at EoLpython
colorama.init(autoreset=True)

# Globally-defined Verkada PoI URL
URL_POI = "https://api.verkada.com/cameras/v1/people/person_of_interest"
URL_LPR = "https://api.verkada.com/cameras/v1/\
analytics/lpr/license_plate_of_interest"

ORG_ID = getenv("lab_id")
API_KEY = getenv("lab_key")

MAX_RETRIES = 10
DEFAULT_RETRY_DELAY = 0.25
BACKOFF = 0.25

# Set logger
log = logging.getLogger()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s"
)
# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Define header and parameters for API requests
HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-api-key": API_KEY
}

PARAMS = {
    "org_id": ORG_ID
}


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


class APIThrottleException(Exception):
    """
    Exception raised when the API request rate limit is exceeded.

    :param message: A human-readable description of the exception.
    :type message: str
    """

    def __init__(self, message="API throttle limit exceeded."):
        self.message = message
        super().__init__(self.message)


def run_thread_with_rate_limit(threads, rate_limit=10,
                               max_events=10, pacing=1):
    """
    Run a thread with rate limiting.

    :param target: The target function to be executed in the thread:
    :type targe: function:
    :return: The thread that was created and ran
    :rtype: thread
    """
    limiter = RateLimiter(rate_limit=rate_limit,
                          max_events_per_sec=max_events, pacing=pacing)

    def run_thread(thread):
        with threading.Lock():
            limiter.acquire()
            log.debug(f"{Fore.LIGHTBLACK_EX}Starting thread{Style.RESET_ALL} \
{thread.name} at time {datetime.datetime.now().strftime('%H:%M:%S')}")
            thread.start()

    for thread in threads:
        run_thread(thread)

    for thread in threads:
        thread.join()


def createPOI(name, image, download):
    """
    Will create a person of interest with a given URL to an image or path to a file

    :param name: The name of the person of interest to be created.
    :type name: str
    :param image: The URL to the image of the person of interest. This image
must be a portrait of a human.
    :type image: str
    :param download: A value of 'y' or 'n' to indicate whether the image needs
to be downloaded. Most cases, the value will be 'y.'
    :type download: str
    :return: None
    :rtype: None
    """
    local_data = threading.local()
    local_data.RETRY_DELAY = DEFAULT_RETRY_DELAY

    file_content = None  # Pre-define

    if download == 'y':
        # Download the JPG file from the URL
        img_response = requests.get(image)

        if img_response.status_code == 200:
            # File was successfully downloaded
            file_content = img_response.content
        else:
            # Handle the case where the file download failed
            log.critical(f"{Fore.RED}Failed to download the image")
    else:
        file_content = image  # No need to parse the file

    # Convert the binary content to base64
    base64_image = base64.b64encode(file_content).decode('utf-8')

    # Set payload
    payload = {
        "label": name,
        "base64_image": base64_image
    }

    try:
        for _ in range(MAX_RETRIES):
            response = requests.post(
                URL_POI, json=payload, headers=HEADERS, params=PARAMS)

            if response.status_code == 429:
                log.debug(f"{Fore.LIGHTBLACK_EX}PERSON - {name} \
{Fore.LIGHTMAGENTA_EX}API throttle.{Style.RESET_ALL} \
Retry in {local_data.RETRY_DELAY}s.")
                
                time.sleep(local_data.RETRY_DELAY)

                local_data.RETRY_DELAY += BACKOFF

            else:
                break

        if response.status_code == 429:
            raise APIThrottleException("API throttled")

        elif response.status_code != 200:
            log.warning(f"{response.status_code}: Could not create {name}")

    except APIThrottleException:
        log.warning(f"{name} Hit API request rate limit of 500/min")

    except Exception as e:
        log.critical(f"Unexpected error: {e}")


def generate_random_string(length):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def createPlate(name, plate):
    """
    Create a LPoI with a given name and license plate number.

    :param name: This is the name that will be used for the description of the
license plate.
    :type name: str
    :param plate: The value of the license plate.
    :type plate: str
    :return: None
    :rtype: None
    """
    local_data = threading.local()
    local_data.RETRY_DELAY = DEFAULT_RETRY_DELAY

    payload = {
        "description": name,
        "license_plate": plate
    }

    try:
        for _ in range(MAX_RETRIES):
            response = requests.post(
                URL_LPR, json=payload, headers=HEADERS, params=PARAMS)

            if response.status_code == 429:
                log.debug(f"{Fore.LIGHTBLACK_EX}PLATE - {name} \
{Fore.LIGHTMAGENTA_EX}API throttle.{Style.RESET_ALL} \
Retry in {local_data.RETRY_DELAY}s.")
                
                time.sleep(local_data.RETRY_DELAY)

                local_data.RETRY_DELAY += BACKOFF

            else:
                break

        if response.status_code == 429:
            raise APIThrottleException("API throttled")

        elif response.status_code != 200:
            log.warning(f"{response.status_code}: Could not create {name}")
            log.warning(f"Response content: {response.text}")

    except APIThrottleException:
        log.warning(f"{name} Hit API request rate limit of 500/min")
    except Exception as e:
        log.critical(f"An unexpected error occurred: {e}")


# Check if the code is being ran directly or imported
if __name__ == "__main__":
    image = 'https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fi.\
pinimg.com%2F736x%2F87%2Fea%2F33%2F87ea336233db8ad468405db8f94da050--human-\
faces-photos-of.jpg&f=1&nofb=1&ipt=6af7ecf6cd0e15496e7197f3b6cb1527beaa8718\
c58609d4feca744209047e57&ipo=images'

    number = False
    while not number:
        try:
            max_interests = int(input("How many (L)PoIs would you \
like to create? "))
            number = True
        except ValueError:
            print("Please enter a valid number!")

    start_time = time.time()
    threads = []
    for i in range(1, max_interests+1):
        name = f'PoI{i}'
        plate = generate_random_string(6)
        plate_name = f'Plate{i}'

        log.info(f"Running for {name} and {plate}")
        thread_poi = threading.Thread(
            target=createPOI, args=(name, image, 'y')
        )
        threads.append(thread_poi)

        thread_lpoi = threading.Thread(
            target=createPlate, args=(plate_name, plate)
        )
        threads.append(thread_lpoi)

    run_thread_with_rate_limit(threads)

    end_time = time.time()
    elapsed_time = end_time - start_time
    log.info(f"Time to complete: {elapsed_time:.2f}")

    print("Complete")
