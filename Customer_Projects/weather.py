"""
Author: Ian Young
Credit: open-meteo for free weather forecasts
End game with this script is to check if there will be any snowfall today.
If there is a chance of snowfall, a message will be sent out to "subscribed"
users.

RULES:
- Please document any changes being made with comments and doc scripts.
- Make sure you are adding appropriate values to log calls
- Please add debug log calls to help troubleshoot.
- We also need to keep emails down to 100/day
- If you are running the script for testing, comment out the function
unless you are testing email functionality specifically.
- Do not hard-code any credentials
"""

# Import essential libraries
import os
import subprocess
import time
from datetime import datetime, timezone
from os import getenv

import requests
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    Disposition,
    FileContent,
    FileName,
    FileType,
    Mail,
)

from tools import log
from tools.api_endpoints import GET_STREAM_TOKEN, STREAM_URL

load_dotenv()  # Load credentials file

# Set environment variables
FOOTAGE_URL = f"{STREAM_URL}?camera_id="
SENDGRID_API_KEY = getenv("")
VERKADA_API_KEY = getenv("")
ORG_ID = getenv("")
CAMERA_ID = getenv("")

# Set timeout responses
MAX_RETRIES = 5  # Number of allowed attempts
RETRY_DELAY = 0.25  # How long to wait between attempts (in seconds)


##############################################################################
#################################  Email  ####################################
##############################################################################


def get_mime(file: str):
    """
    Will determine the MIME of a given file

    :param file: The file name to get the MIME from.
    :type file: str
    :return: The MIME value of the file
    :rtype: str
    """
    # (almost) All image MIME mappings
    mime_types = {
        ".bm": "image/bmp",
        ".bmp": "image/bmp",
        ".gif": "image/gif",
        ".jfif": "image/jfif",
        ".jfif-tbnl": "image/jfif-tbnl",
        ".jpe": "image/jpe",
        ".jpeg": "image/jpeg",
        ".jpg": "image/jpg",
        ".jps": "image/jps",
        ".jut": "image/jutvision",
        ".mcf": "image/vasa",
        ".nap": "image/nap",
        ".naplps": "image/naplps",
        ".nif": "image/x-nif",
        ".niff": "image/x-niff",
        ".pbm": "image/x-portable-bitmap",
        ".pct": "image/x-pict",
        ".pcx": "image/x-pcx",
        ".pgm": "image/x-portable-graymap",
        ".pnm": "image/x-portable-anymap",
        ".ppm": "image/x-portable-pixmap",
        ".qif": "image/x-quicktime",
        ".qti": "image/x-quicktime",
        ".qtif": "image/x-quicktime",
        ".rf": "image/vnd.rn-realflash",
        ".rgb": "image/x-rgb",
        ".svf": "image/vnd.dwg",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".wbmp": "image/vnd.wap.wbmp",
        ".xif": "image/vnd.xiff",
    }

    _, extension = os.path.splitext(file)

    mime = mime_types.get(extension.lower())

    if mime is None:
        raise ValueError(f"MIME type could not be found for file {file}")

    return mime


def send_snow(
    sender_email: str,
    sender_name: str,
    recipient_list: list,
    snow,
    image_name: str,
):
    """
    Sends an email with the expected amount of snow today.

    :param sender_email: Displayed sender email.
    :type sender_email: str
    :param sender_name: Name of sender in the email.
    :type sender_name: str
    :param recipient_list: List of subscribed recipients.
    :type recipient_list: list
    :param snow: Expected amount of snowfall in the next 24 hours.
    :type snow: int
    :param image_name: The name/path of the image file that is to be sent out.
    :type image_name: str
    """
    try:
        for recipient_email in recipient_list:
            for _ in range(MAX_RETRIES):
                # Compile the message
                message = Mail(
                    from_email=f"{sender_name} <{sender_email}>",
                    to_emails=recipient_email,
                    subject="Snowfall Expected Today",
                    plain_text_content=f"Expected snowfall today: {snow} inches.",
                )

                # Attach the image to the email
                with open(image_name, "rb") as file:
                    data = file.read()
                    file_name = os.path.basename(image_name)
                    file_type = get_mime(image_name)

                    # Compile the image attachment
                    attachment = Attachment(
                        FileContent(data),
                        FileName(file_name),
                        FileType(file_type),
                        Disposition("attachment"),
                    )

                message.add_attachment(attachment)  # Add the attachment

                if SENDGRID_API_KEY is None:
                    raise ValueError("SENDGRID_API_KEY is not set.")
                sendgrid = SendGridAPIClient(
                    SENDGRID_API_KEY
                )  # Load the API client

                log.debug("Making email send request.")
                response = sendgrid.send(message)
                log.debug("Email request sent.")

                if response.status_code == 504:
                    log.warning(
                        "Sending timeout. Retrying in %ds.", RETRY_DELAY
                    )
                    time.sleep(RETRY_DELAY)

                else:
                    log.debug(
                        "Request received. Request status code: %d",
                        response.status_code,
                    )

                    break  # Stop retrying once request is received

            if response.status_code != 200:
                log.error("Error sending email: %d", response.status_code)

    except FileNotFoundError:
        log.critical("Could not pull the image.")


##############################################################################
################################  Weather  ###################################
##############################################################################


def get_snowfall_data(latitude, longitude):
    """
    Makes a request to get a 7 day forecast of snowfall. The response is 1 day
    back, today, and 5 days out.
    :param latitude: Latitude of the target location.
    :type latitude: int
    :param longitude: Longitude of the target location.
    :type longitude: int
    :return: Returns the JSON-formatted data
    :rtype: str
    """
    base_url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "snowfall_sum",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timeformat": "unixtime",
        "timezone": "America/Denver",
    }

    for _ in range(MAX_RETRIES):
        log.debug("Sending weather request.")
        response = requests.get(base_url, params=params, timeout=5)
        log.debug("Request received: %d", response.status_code)

        if response.status_code != 504:
            break  # Didn't time out, leave loop

        log.warning("Timeout. Retrying in: %ds.", RETRY_DELAY)
        time.sleep(RETRY_DELAY)

    data = response.json()  # Format the raw data to JSON

    if response.status_code == 200:
        return data

    log.critical(
        "Error %d: %s",
        response.status_code,
        str(data.get("error", "Unknown error")),
    )
    return None


def get_snowfall(data):
    """
    Takes JSON-formatted data and returns true or false on whether or not snow
    is expected today.
    :param data: JSON-formatted weather data
    :type data: str
    :return: Returns how much snowfall is expected (inches) today.
    :rtype: int
    """
    # Extract snowfall information from the response
    times = data["daily"]["time"]
    snowfall_values = data["daily"]["snowfall_sum"]

    today = datetime.fromtimestamp(times[0], timezone.utc).strftime("%m-%d")
    snowfall_today = snowfall_values[0]

    if snowfall_today is not None:
        log.info(
            "%s Chance of snowfall today: %s inches",
            str(today),
            str(snowfall_today),
        )
        return int(snowfall_today)

    log.info("No forecast data available for today.")
    return 0


##############################################################################
#################################  Stream  ###################################
##############################################################################


def get_token():
    """
        Generates a JWT token for the streaming API. This token will be integrated
    inside of a link to grant access to footage.

        :return: Returns the JWT token to allow access via a link to footage.
        :rtype: str
    """
    # Define the request headers
    headers = {"x-api-key": VERKADA_API_KEY}

    # Set the parameters of the request
    params = {"org_id": ORG_ID, "expiration": 30}

    # Send GET request to get the JWT
    response = requests.get(
        GET_STREAM_TOKEN, headers=headers, params=params, timeout=5
    )

    if response.status_code == 200:
        # Parse the response
        data = response.json()

        return data.get("jwt")

    # In case the GET was not successful
    print(f"Failed to retrieve token. Status code: {response.status_code}")
    return None


def load_stream(image_name: str, jwt: str, camera_id: str):
    """
    Loads the HLS video and saves a snapshot of the first frame of the clip.

    :param jwt: The token that grants the API access to the footage.
    :type jwt: str
    :param camera_id: The camera ID of the device to pull footage from.
    :type camera_id: str
    :return: None
    :rtype: None
    """
    # Format the links
    live_link = (
        f"{FOOTAGE_URL}{camera_id}&org_id={ORG_ID}&resolution=high_res"
        f"&jwt={jwt}&type=stream"
    )

    # Set the commands to run that will save the images
    live_image = [
        "ffmpeg",
        "-y",
        "-i",
        live_link,
        "-frames:v",
        "1",
        f"./{image_name}",
        "-loglevel",
        "quiet",
    ]

    # Output the file
    subprocess.run(live_image, check=False)


##############################################################################
##################################  Misc  ####################################
##############################################################################


def main():
    """
    Perform weather-related actions based on the snowfall data at a
    specified latitude and longitude.

    Returns:
        None
    """
    latitude = 40.746216  # Replace with the desired latitude
    longitude = -111.90541  # Replace with the desired longitude

    if snowfall_data := get_snowfall_data(latitude, longitude):
        snow_today = get_snowfall(snowfall_data)

        if snow_today > 0:
            image_name = "live_screenshot.jpg"

            load_stream(image_name, get_token(), CAMERA_ID)
            recipients = ["ian.young@verkada.com"]
            send_snow(
                "dnr-weather@dnr-verkada-api.com",
                "dnr-weather",
                recipients,
                snow_today,
                image_name,
            )


# Check if the file is being imported or ran directly
if __name__ == "__main__":
    main()
