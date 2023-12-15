# Author: Ian Young
# Credit: open-meteo for free weather forecasts

import requests
import logging
from datetime import datetime

# Set the logger
log = logging.getLogger()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


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

    log.DEBUG("Sending weather request.")
    response = requests.get(base_url, params=params)
    log.debug(f"Request received: {response.status_code}")

    data = response.json()

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
    :return: True or False value on whether snow is expected
    :rtyoe: bool
    """
    # Extract snowfall information from the response
    times = data['daily']['time']
    snowfall_values = data['daily']['snowfall_sum']

    today = datetime.utcfromtimestamp(times[0]).strftime('%m-%d')
    snowfall_today = snowfall_values[0]

    if snowfall_today is not None and snowfall_today > 0:
        log.info(f"{today} Chance of snowfall today: {snowfall_today} inches")

    elif snowfall_today == 0:
        log.info(f"{today}No snow is expected today.")

    else:
        log.info("No forecast data available for today.")


def main():
    """Driving function."""
    slc_latitude = 40.746216  # Replace with the desired latitude
    slc_longitude = -111.90541  # Replace with the desired longitude

    latitude = 61.45  # A snowy place
    longitude = 5.82  # A snowy place

    snowfall_data = get_snowfall_data(slc_latitude, slc_longitude)

    if snowfall_data:
        get_snowfall(snowfall_data)


# Check if the file is being imported or ran directly
if __name__ == "__main__":
    main()
