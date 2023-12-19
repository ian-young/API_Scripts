# Author: Ian Young
# Credit: open-meteo for free weather forecasts
# End game with this script is to check if there will be any snowfall today.
# If there is a chance of snowfall, a message will be sent out to "subscribed"
# users.

# RULES:
# - Please document any changes being made with comments and doc scripts.
# - Make sure you are adding approriate values to log calls
# - Please add debug log calls to help troubleshoot.
# - We also need to keep emails down to 100/day
#    - If you are running the script for testing, comment out the function
# unless you are testing email functionality specifically.
# - Do not hard-code any credentials

# Import libraries
import requests
import logging
import time
import creds
import os
import subprocess

# Cleanup the namespace a little
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, Disposition
from sendgrid.helpers.mail import FileContent, FileName, FileType

# Set the logger
log = logging.getLogger()
logging.basicConfig(
    level = logging.DEBUG,
    format = "%(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Set environment variables
TOKEN_URL = "https://api.verkada.com/cameras/v1/footage/token"
STREAM_URL = "https://api.verkada.com/stream/cameras/v1/footage/stream/stream.m3u8"
SENDGRID_API_KEY = creds.sendgrid_key
VERKADA_API_KEY = creds.slc_stream_key
ORG_ID = creds.slc_id
CAMERA_ID = creds.slc_camera_id

# Set timeout responses
MAX_RETRIES = 5  # Number of allowed attempts
RETRY_DELAY = 0.25  # How long to wait between attempts (in seconds)


##############################################################################
                                # Email #
##############################################################################


def get_mime(file: str):
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


def send_snow(sender_email: str, sender_name: str, recipient_list: list,
              snow, image_name: str):
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
    subject = "Snowfall Expected Today"
    body = f"Expected snowfall today: {snow} inches."

    try:
        for recipient_email in recipient_list:
            for _ in range(MAX_RETRIES):
                # Compile the message
                message = Mail(
                    from_email=f'{sender_name} <{sender_email}>',
                    to_emails=recipient_email,
                    subject=subject,
                    plain_text_content=body
                )

                # Attach the image to the email
                with open(image_name, 'rb') as file:
                    data = file.read()
                    file_name = os.path.basename(image_name)
                    file_type = get_mime(image_name)

                    # Compile the image attachment
                    attachment = Attachment(
                        FileContent(data),
                        FileName(file_name),
                        FileType(file_type),
                        Disposition('attachment')
                    )

                message.attachment = attachment  # Add the attachment

                sendgrid = SendGridAPIClient(
                    SENDGRID_API_KEY)  # Load the API client

                log.debug("Making email send request.")
                response = sendgrid.send(message)
                log.debug("Email request sent.")

                if response.status_code == 504:
                    log.warning(
                        f"Sending timeout. Retrying in {RETRY_DELAY}s.")
                    time.sleep(RETRY_DELAY)

                else:
                    log.debug(
                        f"Request received."
                        f"Request status code: {response.status_code}."
                    )

                    break  # Stop retrying once request is received

            if response.status_code != 200:
                log.error(f"Error sending email: {response.status_code}")

    except FileNotFoundError as e:
        log.critical("Could not pull the image.")


##############################################################################
                                # Weather #
##############################################################################


def get_snowfall_data(latitude, longitude):
    """
    Makes a request to get a 7 day forecast of snowfall. The response is 1 day
    back, today, and 5 days out.
    :param latitude: Latitude of the target location.
    :type latitude: int
    :param longitude: Longitude of the target location.
    :type longitude: int
    :return: Retuurns the JSON-formatted data
    :rtype: str
    """
    base_url = "https://api.open-meteo.com/v1/forecast"

    params = {
        'latitude': latitude,
        'longitude': longitude,
        'daily': 'snowfall_sum',
        'temperature_unit': 'fahrenheit',
        'wind_speed_unit': 'mph',
        'precipitation_unit': 'inch',
        'timeformat': 'unixtime',
        'timezone': 'America/Denver'
    }

    for _ in range(MAX_RETRIES):
        log.debug("Sending weather request.")
        response = requests.get(base_url, params=params)
        log.debug(f"Request received: {response.status_code}")

        if response.status_code == 504:
            log.warning(f"Timeout. Retrying in: {RETRY_DELAY}s.")
            time.sleep(RETRY_DELAY)

        else:
            break  # Didn't time out, leave loop

    data = response.json()  # Format the raw data to JSON

    if response.status_code == 200:
        return data

    else:
        log.critical(
            f"Error {response.status_code}: "
            f"{data.get('error', 'Unknown error')}")
        return None


def get_snowfall(data):
    """
    Takes JSON-formatted data and returns true or false on whether or not snow
    is expected today.
    :param data: JSON-formatted weather data
    :type data: str
    :return: Returns how much snowfall is expected (inches) today.
    :rtyoe: int
    """
    # Extract snowfall information from the response
    times = data['daily']['time']
    snowfall_values = data['daily']['snowfall_sum']

    today = datetime.utcfromtimestamp(times[0]).strftime('%m-%d')
    snowfall_today = snowfall_values[0]

    if snowfall_today is not None:
        log.info(f"{today} Chance of snowfall today: {snowfall_today} inches")
        return int(snowfall_today)

    else:
        log.info("No forecast data available for today.")
        return 0


##############################################################################
                                # Stream #
##############################################################################


def getToken():
    """
    Generates a JWT token for the streaming API. This token will be integrated
inside of a link to grant access to footage.

    :return: Returns the JWT token to allow access via a link to footage.
    :rtype: str
    """
    # Define the request headers
    headers = {
        'x-api-key': VERKADA_API_KEY
    }

    # Set the parameters of the request
    params = {
        'org_id': ORG_ID,
        'expiration': 30
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


def loadStream(image_name: str, jwt: str, camera_id: str):
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
    live_link = 'https://api.verkada.com/stream/cameras/v1/footage/stream/stream.m3u8?camera_id=' + \
        camera_id + '&org_id=' + ORG_ID + \
        '&resolution=high_res&jwt=' + jwt + '&type=stream'

    # Set the commands to run that will save the images
    live_image = ['ffmpeg', '-y', '-i', live_link,
                  '-frames:v', '1', f'./{image_name}', '-loglevel', 'quiet']

    # Output the file
    subprocess.run(live_image)




##############################################################################
                                # Misc #
##############################################################################


def main():
    """Driving function."""
    recipients = ["ian.young@verkada.com"]
    image_name = "live_screenshot.jpg"

    slc_latitude = 40.746216  # Replace with the desired latitude
    slc_longitude = -111.90541  # Replace with the desired longitude

    latitude = 61.45  # A snowy place
    longitude = 5.82  # A snowy place

    snowfall_data = get_snowfall_data(slc_latitude, slc_longitude)

    if snowfall_data:
        snow_today = get_snowfall(snowfall_data)

        if snow_today > 0:
            loadStream(image_name, getToken(), CAMERA_ID)
            send_snow("dnr-weather@dnr-verkada-api.com",
                      "dnr-weather", recipients, snow_today, image_name)


# Check if the file is being imported or ran directly
if __name__ == "__main__":
    main()
