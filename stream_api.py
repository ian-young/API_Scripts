"""
Author: Ian Young
Purpose: Save and print/open a screenshot from a given camera at a given time.
"""
# Import essential libraries
import datetime
import logging
import subprocess
from os import getenv

import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()  # Load credentials file

TOKEN_URL = "https://api.verkada.com/cameras/v1/footage/token"
STREAM_URL = "https://api.verkada.com/stream/cameras/v1/footage/stream/stream.m3u8"

API_KEY = getenv("")
ORG_ID = getenv("")
CAMERA = ""  # Can be a list or single String

log = logging.getLogger()
log.setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)


def get_token(org_id=ORG_ID, api_key=API_KEY):
    """
    Generates a JWT token for the streaming API. This token will be integrated
    inside of a link to grant access to footage.

    :param org_id: The target organization ID.
    :type org_id: str, optional
    :param api_key: The API key to authenticate with
    :type api_key: str, optional
    :return: a JWT token to stream camera footage.
    :rtype: str
    """

    # Define the request headers
    headers = {
        'x-api-key': api_key
    }

    # Set the parameters of the request
    params = {
        'org_id': org_id,
        'expiration': 60
    }

    # Send GET request to get the JWT
    response = requests.get(TOKEN_URL, headers=headers,
                            params=params, timeout=5)

    if response.status_code == 200:
        # Parse the response
        data = response.json()

        # Extract the token
        jwt = data.get('jwt')

        return jwt
    else:
        # In case the GET was not successful
        print(f"Failed to retrieve token. Status code: {response.status_code}")
        return None


def load_stream(jwt, camera_id, stream_start_time, org_id=ORG_ID):
    """
    Loads the HLS video and saves a snapshot of the first frame.

    :param jwt: The authenticated JWT token to allow for video streaming.
    :type jwt: str
    :param camera_id: The Verkada camera device-id value.
    :type camera_id: str
    :param stream_start_time: The time to start the streaming video at.
    :type stream_start_time: int
    :param org_id: The target organization ID.
    :type org_id: str, optional
    """

    # Bring the end time to one second ahead of the start time
    stream_end_time = stream_start_time + 1

    # Format the links
    base_url = 'https://api.verkada.com/stream/cameras/v1/footage/stream/\
stream.m3u8?camera_id='
    live_link = base_url + camera_id + '&org_id=' + org_id + \
        '&resolution=high_res&jwt=' + jwt + '&type=stream'
    historical_link = live_link + '&start_time=' + \
        str(stream_start_time) + '&end_time=' + str(stream_end_time)

    # Set the commands to run that will save the images
    still_image_live = ['ffmpeg', '-y', '-i', live_link,
                        '-frames:v', '1', './live_screenshot.jpeg', '-loglevel', 'quiet']

    his_still_image = ['ffmpeg', '-y', '-i', historical_link,
                       '-frames:v', '1', './historical_screenshot.jpeg', '-loglevel', 'quiet']
    try:
        # Output the file
        subprocess.run(still_image_live, check=True)

        # Print the image (low-res) in terminal
        print_image('live_screenshot.jpeg')

        # Output the file
        subprocess.run(his_still_image, check=True)

        # Print the image (low-res) in terminal
        print_image('historical_screenshot.jpeg')

    except subprocess.CalledProcessError as e:
        print("An error has occured when trying to process the image in the \
terminal\n%s", e)


def print_image(file_name):
    """
    Will print a given image into the terminal in very low resolution.

    :param file_name: The name of the image file to print into the terminal.
    :type file_name: str
    :return: None
    :rtype: None
    """

    try:
        subprocess.run(['timg', file_name], check=True)
    except subprocess.CalledProcessError as e:
        print("An error has occured when trying to print the image in the \
terminal\n%s", e)

    # --------------------------
    # If using Pillow and you want a higher-res image displayed
    # NOTE: This won't be displayed in the terminal
    # Load the image
    image = Image.open(file_name)

    # Print the image
    image.show()


def epoch(e_year, e_month, e_day, e_hour, e_minute):
    """
    Converts a given time to an epoch timestamp and returns the integer value.

    :param e_year: The year value to convert to an epoch timestamp.
    :type e_year: int
    :param e_month:The month value to convert to an epoch timestamp.
    :type e_month: int
    :param e_day:The year day to convert to an epoch timestamp.
    :type e_day: int
    :param e_hour:The year hour to convert to an epoch timestamp.
    :type e_hour: int
    :param e_minute:The minute value to convert to an epoch timestamp.
    :type e_minute: int
    :return: An epoch timestamp in milliseconds
    :rtype: int
    """

    # Define the date and time in Python terms
    py_time = datetime.datetime(e_year, e_month, e_day, e_hour, e_minute)

    # Convert to epoch timestamp (seconds since Jan 1, 1970)
    epoch_timestamp = int(py_time.timestamp())

    return epoch_timestamp


# Check if being ran directly or is imported by another program
if __name__ == "__main__":
    # org = str(input("Org ID: "))
    # key = str(input("API key: "))
    CID = str(input("ID of the camera to pull from: "))
    year = int(input("Year of search: "))
    month = int(input("Month of search (integer): "))
    day = int(input("Day of search (integer): "))
    hour = int(input("Hour of search (24-hour clock): "))
    minute = int(input("Minute of search: "))

    start_time = epoch(year, month, day, hour, minute)

    token = get_token()

    # Check if the token is null
    if token and CAMERA is not "":
        if isinstance(CAMERA, list):
            log.debug("List provided -> Checking if list is iterable.")

            if hasattr(CAMERA, "__iter__"):
                log.debug(
                    "List provided -> list is iterable -> attempting triggers.")

                for target in CAMERA:
                    load_stream(token, target, start_time)

            else:
                log.critical("List is not iterable.")

        # Run for a single lockdown
        else:
            load_stream(token, CAMERA, start_time)
    elif token:
        if isinstance(CID, list):
            log.debug("List provided -> Checking if list is iterable.")

            if hasattr(CID, "__iter__"):
                log.debug(
                    "List provided -> list is iterable -> attempting triggers.")

                for target in CID:
                    load_stream(token, target, start_time)

            else:
                log.critical("List is not iterable.")

        # Run for a single lockdown
        else:
            load_stream(token, CID, start_time)
    else:
        print("Failed to get token, terminating application.")
