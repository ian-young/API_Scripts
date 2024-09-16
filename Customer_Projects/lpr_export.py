"""
Authors: Ian Young, Elmar Aliyev
Purpose: Will retrieve all seen plates in the past 24 hours and save
    the data in a csv. This is meant to be used for scheduled exports.
"""

from datetime import datetime, timedelta
from os import getenv
from typing import List, Dict, Union

import requests
import pandas as pd
from dotenv import load_dotenv

from tools import log
from tools.custom_exceptions import APIExceptionHandler
from tools.api_endpoints import GET_SEEN_PLATES, GET_CAMERA_DATA

load_dotenv()  # Load credentials

API_KEY = getenv("")
CURRENT_TIME = datetime.now()
END_TIME = int(CURRENT_TIME.timestamp())
CSV_OUTPUT = f"lpr_info-{datetime.now().date()}.csv"
CSV_CAMERAS = "cameras.csv"
START_TIME = int((CURRENT_TIME - timedelta(days=1)).timestamp())

HEADERS = {}  # Initialize
if API_KEY := getenv(""):
    HEADERS = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY,
    }


def convert_epoch_to_time(epoch_time: float) -> str:
    """
    Converts an epoch time to a formatted time string.

    Args:
        epoch_time (float): The epoch time to convert.

    Returns:
        str: The formatted time string in the format "%H:%M:%S".
    """
    return datetime.fromtimestamp(epoch_time).strftime("%H:%M:%S")


def parse_cameras() -> List[Dict[str, str]]:
    """
    Parse camera data to retrieve device IDs.

    Args:
        None

    Raises:
        APIExceptionHandler: If an error occurs during the API request.

    Returns:
        list of dict: A list of device IDs and their assigned sites.
    """
    device_ids: List[Dict[str, str]] = []

    if HEADERS:
        lpr_cameras = {"CB52-E", "CB62-E", "CB52-TE", "CB62-TE"}
        try:
            log.info("Request cameras list.")
            response = requests.get(
                GET_CAMERA_DATA, headers=HEADERS, timeout=5
            )
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

    log.debug("Returning %s", device_ids)

    return device_ids


def get_plates(camera_ids: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Get license plates seen by a specific camera.

    Args:
        camera_id (dict): The ID of the camera and its assigned site.

    Raises:
        APIExceptionHandler: If an error occurs during the API request.

    Returns:
        list of dict: A formatted list of dictionary values with a
            license plate value, the camera it was seen by, the time, it
            was seen at, and the site the camera resides in.
    """
    final_dict: List[Dict[str, str]] = []

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
                GET_SEEN_PLATES, headers=HEADERS, params=body, timeout=3
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

            # Check if there are more pages
            if data["next_page_token"] is not None:
                body = {
                    "camera_id": camera["ID"],
                    "start_time": START_TIME,
                    "end_time": END_TIME,
                    "page_token": data["next_page_token"],
                }

        except APIExceptionHandler as e:
            raise APIExceptionHandler(e, response, "Get License Plates") from e

    return final_dict


all_plate_info = get_plates(parse_cameras())

# Convert the list of dictionaries to a DataFrame
df = pd.DataFrame(all_plate_info)

# Write the DataFrame to a CSV file
df.to_csv(CSV_OUTPUT, index=False, encoding="UTF-8")

print(f"CSV file {CSV_OUTPUT} created with {len(df)} records.")
