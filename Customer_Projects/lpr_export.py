"""
Author: Ian Young
Purpose: Will retrieve all seen plates in the past 24 hours and save the
    the data in a csv.
"""

import csv
import logging
from datetime import datetime, timedelta
from os import getenv

import requests
from dotenv import load_dotenv

from QoL.custom_exceptions import APIExceptionHandler
from QoL.api_endpoints import GET_SEEN_PLATES, GET_CAMERA_DATA

log = logging.getLogger()
LOG_LEVEL = logging.DEBUG
log.setLevel(LOG_LEVEL)
logging.basicConfig(
    level=LOG_LEVEL, format="%(asctime)s - %(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

load_dotenv()  # Load credentials

API_KEY = getenv("lab_key")
CURRENT_TIME = datetime.now()
START_TIME = int(CURRENT_TIME.timestamp())
CSV_OUTPUT = f"lpr_info-{datetime.now().date()}.csv"
CSV_CAMERAS = "cameras.csv"
END_TIME = int((CURRENT_TIME - timedelta(days=1)).timestamp())


def parse_cameras(api_key=API_KEY):
    """
    Parse camera data to retrieve device IDs.

    Args:
        api_key (str): The API key for authentication.

    Raises:
        APIExceptionHandler: If an error occurs during the API request.

    Returns:
        list: A list of device IDs.
    """
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": api_key,
    }
    device_ids = []

    try:
        # [ ] TODO: Filter out the cameras that don't support LPR
        log.info("Request cameras list.")
        response = requests.get(GET_CAMERA_DATA, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        log.debug(data["cameras"])
        device_ids.extend(device["camera_id"] for device in data["cameras"])
        log.info("List retrieved.")

    except APIExceptionHandler as e:
        raise APIExceptionHandler(e, response, "Get Camera Data") from e

    return device_ids


def get_plates(camera_id, api_key=API_KEY):
    """
    Get license plates seen by a specific camera.

    Args:
        camera_id (str): The ID of the camera.
        api_key (str): The API key for authentication.

    Raises:
        APIExceptionHandler: If an error occurs during the API request.

    Returns:
        None
    """

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": api_key,
    }
    body = {
        "camera_id": camera_id,
        "start_time": START_TIME,
        "end_time": END_TIME,
    }

    try:
        response = requests.post(
            GET_SEEN_PLATES, headers=headers, json=body, timeout=3
        )
        response.raise_for_status()
        data = response.json()
        # [ ] TODO: Parse data

    except APIExceptionHandler as e:
        raise APIExceptionHandler(e, response, "Get License Plates") from e


cameras = parse_cameras()
all_plate_info = (get_plates(camera) for camera in cameras)
with open(CSV_OUTPUT, "w", newline="", encoding="UTF-8") as file:
    fieldnames = ("Time", "Plate", "Camera", "Site")
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_plate_info)
