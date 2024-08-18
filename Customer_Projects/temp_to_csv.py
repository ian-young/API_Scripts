"""
Author:
    Ian Young
Purpose: 
    Fetches temperature data from a specified device using the
    Verkada API, appends the data to a CSV file, and filters out old data
    based on a specified number of days to keep.

Raises:
    custom_exceptions.APIExceptionHandler: If there is an issue with the
    API request.
"""

import logging
from datetime import datetime, timedelta
from os import environ, getenv
from typing import Any, Dict, Generator, List, Union

import pandas as pd
import requests
from dotenv import load_dotenv

import QoL.custom_exceptions as custom_exceptions

environ.clear()  # Clear any previously loaded variables
load_dotenv()  # Import credentials

# Set logger
log = logging.getLogger()
log.setLevel(logging.ERROR)
logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Constants
DEVICE_ID = getenv("lab_sensor")
API_KEY = getenv("lab_key")
CURRENT_TIME = datetime.now()
END_TIME = int(CURRENT_TIME.timestamp())
START_TIME = int((CURRENT_TIME - timedelta(days=1)).timestamp())
PAGE_TOKEN = 1
PAGE_SIZE = 200
FIELDS = "temperature"
INTERVAL = "5m"
BASE_URL = "https://api.verkada.com/environment/v1/data"
CSV_FILE = "temperature_data.csv"
DAYS_TO_KEEP = 7
HEADERS = {
    "accept": "application/json",
    "x-api-key": API_KEY,
}


def celsius_to_fahrenheit(temp_value: float) -> float:
    """
    Convert a temperature value from Celsius to Fahrenheit.

    Args:
        temp_value (float): The temperature value in Celsius.

    Returns:
        float: The temperature value converted to Fahrenheit.
    """
    return temp_value * (9 / 5) + 32


def fetch_all_data() -> List[Dict[str, Union[str, int]]]:
    """
    Fetches all temperature data from the API, appends the data to CSV,
    and filters out old data based on a specified number of days to keep.

    Returns:
        list: Updated list of filtered data (rows) to write to CSV.
    """
    filtered_data = []

    try:
        url = f"{BASE_URL}?device_id={DEVICE_ID}\
&start_time={START_TIME}&end_time={END_TIME}\
&page_size={PAGE_SIZE}&fields={FIELDS}&interval={INTERVAL}"

        while url:
            response = requests.get(url, headers=HEADERS, timeout=5)
            response.raise_for_status()
            data = response.json()
            temperature_data = data.get("data", [])
            device_name = data.get("device_name", "")

            # Parse the JSON response and append new data
            for entry in temperature_data:
                entry_time = datetime.fromtimestamp(entry["time"])
                if entry_time >= cutoff_time:
                    filtered_data.append(
                        {
                            "Time": entry_time.isoformat(),
                            "Temperature": celsius_to_fahrenheit(
                                entry["temperature"]
                            ),
                            "Device Name": device_name,
                        }
                    )

            # Check if there are more pages to fetch
            if data["next_page_token"] is not None:
                url = f"{BASE_URL}?device_id={DEVICE_ID}&page_token=\
{data['next_page_token']}&page_size={PAGE_SIZE}&fields={FIELDS}&interval={INTERVAL}"

    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(e, response, "sv") from e

    return filtered_data


# Read existing CSV data and filter out old data
cutoff_time = CURRENT_TIME - timedelta(days=DAYS_TO_KEEP)

# Read existing CSV data and filter out old data
try:
    df = pd.read_csv(CSV_FILE, parse_dates=["Time"])
    df = df[df["Time"] >= cutoff_time.isoformat()]
except FileNotFoundError:
    df = pd.DataFrame(columns=["Time", "Temperature", "Device Name"])

# Fetch new data from the API
new_data = fetch_all_data()
new_df = pd.DataFrame(new_data)

# Combine old and new data
combined_df = pd.concat([df, new_df]).drop_duplicates(subset=["Time"])

# Write the updated data back to the CSV
combined_df.to_csv(CSV_FILE, index=False)

print("Temperature data updated.")