# Author: Ian Young
# Purpose: Print two thumbnails from given camera(s) in the terminal. The
# thumbnails are pulled from the live footage and from a targeted time.

import requests
from PIL import Image
import subprocess
import datetime
import creds
import logging

TOKEN_URL = "https://api.verkada.com/cameras/v1/footage/token"
STREAM_URL = "https://api.verkada.com/stream/cameras/v1/footage/stream/stream.m3u8"
API_KEY = creds.lab_key
ORG_ID = creds.lab_id
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


def getToken(org_id=ORG_ID, api_key=API_KEY):
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
    response = requests.get(TOKEN_URL, headers=headers, params=params)

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


def loadStream(jwt, camera_id, start_time, org_id=ORG_ID):
    """
    Loads the HLS video and saves a snapshot of the first frame of the clip.

    :param jwt: The token that grants the API access to the footage.
    :type jwt: str
    :param camera_id: The camera ID of the device to pull footage from.
    :type camera_id: str
    :param start_time: The start time for the footage to pull from the camera.
    :type start_time: str
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :return: None
    :rtype: None
    """

    # Bring the end time to one second ahead of the start time
    end_time = start_time + 1

    # Format the links
    live_link = 'https://api.verkada.com/stream/cameras/v1/footage/stream/stream.m3u8?camera_id=' + \
        camera_id + '&org_id=' + org_id + \
        '&resolution=high_res&jwt=' + jwt + '&type=stream'
    historical_link = live_link + '&start_time=' + \
        str(start_time) + '&end_time=' + str(end_time)

    # Set the commands to run that will save the images
    still_image_live = ['ffmpeg', '-y', '-i', live_link,
                        '-frames:v', '1', './live_screenshot.jpeg', '-loglevel', 'quiet']

    his_still_image = ['ffmpeg', '-y', '-i', historical_link,
                       '-frames:v', '1', './historical_screenshot.jpeg', '-loglevel', 'quiet']

    # Output the file
    subprocess.run(still_image_live)

    # Print the image (low-res) in terminal
    printImage('live_screenshot.jpeg')

    # Output the file
    subprocess.run(his_still_image)

    # Print the image (low-res) in terminal
    printImage('historical_screenshot.jpeg')


def printImage(file_name):
    """
    Will print a given image into the terminal in very low resolution.

    :param file_name: The name of the image file to print into the terminal.
    :type file_name: str
    :return: None
    :rtype: None
    """

    try:
        subprocess.run(['timg', file_name])
    except Exception as e:
        print(f"An error has occured when trying to print the image in the terminal")

    # --------------------------
    # If using Pillow and you want a higher-res image displayed
    # NOTE: This won't be displayed in the terminal
    # Load the image
    # image = Image.open(file_name)

    # Print the image
    # image.show()


def epoch(year, month, day, hour, minute):
    """
    Converts a given time to an epoch timestamp and returns the integer value.

    :param year: The target year to return in the epoch timestamp.
    :type year: int
    :param month: The target month to return in the epoch timestamp.
    :type month: int
    :param day: The target day to return in the epoch timestamp.
    :type day: int
    :param hour: The target hour to return in the epoch timestamp.
    :type hour: int
    :param minute: The target minute to return in the epoch timestamp.
    :type minute: int
    :return: Returns the epoch timestamp.
    :rtype: int
    """

    # Define the date and time in Python terms
    py_time = datetime.datetime(year, month, day, hour, minute)

    # Convert to epoch timestamp (seconds since Jan 1, 1970)
    epoch_timestamp = int(py_time.timestamp())

    return epoch_timestamp


# Check if being ran directly or is imported by another program
if __name__ == "__main__":

    cid = str(input("ID of the camera to pull from: "))
    year = int(input("Year of search: "))
    month = int(input("Month of search (integer): "))
    day = int(input("Day of search (integer): "))
    hour = int(input("Hour of search (24-hour clock): "))
    minute = int(input("Minute of search: "))

    start_time = epoch(2023, 12, 14, 9, 29)

    token = getToken()

    # Check if the token is null
    if token:
        if isinstance(CAMERA, list):
            log.debug("List provided -> Checking if list is iterable.")

            if hasattr(CAMERA, "__iter__"):
                log.debug(
                    "List provided -> list is iterable -> attempting triggers.")

                for target in CAMERA:
                    loadStream(token, target, start_time)

            else:
                log.critical("List is not iterable.")

        # Run for a single lockdown
        else:
            loadStream(token, CAMERA, start_time)
    else:
        print("Failed to get token, terminating application.")
