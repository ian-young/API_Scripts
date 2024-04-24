# Author: Ian Young
# Comment out the constant API Key and Org ID and uncomment the inputs in the main method
# to allow for manual input. You will need to install timg in order to print in terminal.

import requests
from PIL import Image
import subprocess
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN_URL = "https://api.verkada.com/cameras/v1/footage/token"
STREAM_URL = "https://api.verkada.com/stream/cameras/v1/footage/stream/stream.m3u8"

API_KEY = os.getenv("slc_stream_key")
ORG_ID = os.getenv("slc_id")
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
    """Generates a JWT token for streaming API"""

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
    """Loads the HLS video and saves a snapshot of the first frame"""

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
    """Will print a given image into the terminal"""

    try:
        subprocess.run(['timg', file_name])
    except Exception as e:
        print(f"An error has occured when trying to print the image in the terminal")

    # --------------------------
    # If using Pillow and you want a higher-res image displayed
    # Load the image
    # image = Image.open(file_name)

    # Print the image
    # image.show()


def epoch(year, month, day, hour, minute):
    """Converts a given time to an epoch timestamp and returns the integer value"""

    # Define the date and time in Python terms
    py_time = datetime.datetime(year, month, day, hour, minute)

    # Convert to epoch timestamp (seconds since Jan 1, 1970)
    epoch_timestamp = int(py_time.timestamp())

    return int(epoch_timestamp)


# Check if being ran directly or is imported by another program
if __name__ == "__main__":
    # org = str(input("Org ID: "))
    # key = str(input("API key: "))
    cid = str(input("ID of the camera to pull from: "))
    year = int(input("Year of search: "))
    month = int(input("Month of search (integer): "))
    day = int(input("Day of search (integer): "))
    hour = int(input("Hour of search (24-hour clock): "))
    minute = int(input("Minute of search: "))

    start_time = epoch(year, month, day, hour, minute)

    token = getToken()

    # Check if the token is null
    if token:
        loadStream(token, cid, start_time)
    else:
        print("Failed to get token, terminating application.")
