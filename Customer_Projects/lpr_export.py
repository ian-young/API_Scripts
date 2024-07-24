"""
Author: Ian Young
Purpose: Will retrieve all seen plates in the past 24 hours and save the
    the data in a csv.
"""

import csv
import logging
from datetime import datetime, timedelta
from os import getenv
from typing import List, Dict, Optional, Union

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
END_TIME = int(CURRENT_TIME.timestamp())
CSV_OUTPUT = f"lpr_info-{datetime.now().date()}.csv"
CSV_CAMERAS = "cameras.csv"
START_TIME = int((CURRENT_TIME - timedelta(days=1)).timestamp())


def convert_epoch_to_time(epoch_time: float) -> str:
    """
    Converts an epoch time to a formatted time string.

    Args:
        epoch_time (float): The epoch time to convert.

    Returns:
        str: The formatted time string in the format "%H:%M:%S".
    """
    return datetime.fromtimestamp(epoch_time).strftime("%H:%M:%S")


def parse_cameras(api_key: Optional[str] = API_KEY) -> List[Dict[str, str]]:
    """
    Parse camera data to retrieve device IDs.

    Args:
        api_key (str): The API key for authentication. (optional)

    Raises:
        APIExceptionHandler: If an error occurs during the API request.

    Returns:
        list of dict: A list of device IDs and their assigned sites.
    """
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": api_key,
    }

    lpr_cameras = ["CB52-E", "CB62-E", "CB52-TE", "CB62-TE"]
    device_ids: List[Dict[str, str]] = []

    try:
        log.info("Request cameras list.")
        response = requests.get(GET_CAMERA_DATA, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        device_ids.extend(
            {
                "ID": device["camera_id"],
                "Site": device["site"],
                "Camera": device["name"],
            }
            for device in data["cameras"]
            if device["model"] in lpr_cameras
        )

    except APIExceptionHandler as e:
        raise APIExceptionHandler(e, response, "Get Camera Data") from e

    log.debug("Returning %s", device_ids)

    return device_ids


def get_plates(
    camera_ids: List[Dict[str, str]], api_key: Optional[str] = API_KEY
) -> List[Dict[str, str]]:
    """
    Get license plates seen by a specific camera.

    Args:
        camera_id (dict): The ID of the camera and its assigned site.
        api_key (str): The API key for authentication. (optional)

    Raises:
        APIExceptionHandler: If an error occurs during the API request.

    Returns:
        None
    """
    final_dict: List[Dict[str, str]] = []

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": api_key,
    }
    for camera in camera_ids:
        log.debug("Running for %s", str(camera))
        body: Dict[str, Union[str, int]] = {
            "camera_id": camera["ID"],
            "start_time": START_TIME,
            "end_time": END_TIME,
        }
        try:
            log.debug("Requesting plates from %s", camera["ID"])
            response = requests.get(
                GET_SEEN_PLATES, headers=headers, params=body, timeout=3
            )

            response.raise_for_status()
            log.debug("Converting response to JSON.")
            data = response.json()

            final_dict.extend(
                {
                    "Time": convert_epoch_to_time(value["timestamp"]),
                    "Plate": value["license_plate"],
                    "Camera": camera["Camera"],
                    "Site": camera["Site"],
                }
                for value in data["detections"]
                if value is not None
            )

        except APIExceptionHandler as e:
            raise APIExceptionHandler(e, response, "Get License Plates") from e

    return final_dict


all_plate_info = get_plates(parse_cameras())

with open(CSV_OUTPUT, "w", newline="", encoding="UTF-8") as file:
    fieldnames = ("Time", "Plate", "Camera", "Site")
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()

    if plate_info_list := [
        plate_info for plate_info in all_plate_info if plate_info is not None
    ]:
        writer.writerows(plate_info_list)
