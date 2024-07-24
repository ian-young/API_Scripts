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

import csv
import logging
from datetime import datetime, timedelta
from os import environ, getenv

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


def celsius_to_fahrenheit(temp_value):
    """
    Convert a temperature value from Celsius to Fahrenheit.

    Args:
        temp_value (float): The temperature value in Celsius.

    Returns:
        float: The temperature value converted to Fahrenheit.
    """
    return temp_value * (9 / 5) + 32


def read_and_filter_csv(file_path, cutoff):
    """
    Reads a CSV file at the specified file path, filters out rows
    based on a cutoff time, and yields the filtered rows.

    Args:
        file_path: The path to the CSV file to read.
        cutoff: The cutoff time to filter rows.

    Returns:
        Yields rows from the CSV file that have a time value greater
        than or equal to the cutoff time.

    Raises:
        FileNotFoundError: Log if the file is not found.
    """
    try:
        with open(file_path, "r", newline="", encoding="utf-8") as data_file:
            reader = csv.DictReader(data_file)
            for row in reader:
                if datetime.fromisoformat(row["Time"]) >= cutoff:
                    yield row
    except FileNotFoundError:
        log.error("Could not find the csv file. Check working directory.")


def fetch_all_data():
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
            url = None
            if data["next_page_token"] is not None:
                url = f"{BASE_URL}?device_id={DEVICE_ID}&page_token=\
{data['next_page_token']}&page_size={PAGE_SIZE}&fields={FIELDS}&interval={INTERVAL}"

    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(e, response, "sv") from e

    return filtered_data


# Read existing CSV data and filter out old data
cutoff_time = CURRENT_TIME - timedelta(days=DAYS_TO_KEEP)

# Fetch all data from API
all_data = list(read_and_filter_csv(CSV_FILE, cutoff_time))
all_data.extend(fetch_all_data())

# Write the updated data back to the CSV
with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:
    fieldnames = ["Time", "Temperature", "Device Name"]
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_data)

print("Temperature data updated.")
