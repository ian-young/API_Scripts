"""
Author: Ian Young
Purpose: To provide a link to a camera at a certain time
to speed up the process of searching for footage.
"""
# Import essential libraries
import datetime
from os import getenv

import requests
from dotenv import load_dotenv

load_dotenv()  # Import credentials file

ORG_ID = getenv("lab_id")
API_KEY = getenv("lab_key")
URL = "https://api.verkada.com/cameras/v1/footage/link"


def month_to_text(month):
    """
    Takes an integer and conver it to text for the correlated month.

    :param month: The integer value of a month.
    :type month: int
    :return: The string of a month name.
    :rtype: str
    """
    months = {
        1: 'January',
        2: 'February',
        3: 'March',
        4: 'April',
        5: 'May',
        6: 'June',
        7: 'July',
        8: 'August',
        9: 'September',
        10: 'October',
        11: 'Novemner',
        12: 'December'
    }

    return months[int(month)]


def ask_time():
    """
    Asks the user for a date and returns an epoch timestamp.
    
    :return: Epoch timestamp of a prompted date.
    :rtype: int
    """
    # Pre-define variables that may be autofilled
    year = None
    month = None
    day = None
    hour = None
    minute = None
    answer = None

    # Load current values
    current_year = int(datetime.datetime.now().date().strftime('%Y'))
    current_month = int(datetime.datetime.now().date().strftime('%m'))
    month_text = month_to_text(current_month)

    while answer not in ['y', 'n']:
        print(f"Is the footage from {current_year}?")
        answer = input("(y/n) ").strip().lower()

    if answer == 'y':
        year = current_year
        answer = None  # reset

        while answer not in ['y', 'n']:
            print(f"Is the footage from {month_text}?")
            answer = input("(y/n) ").strip().lower()

        if answer == 'y':
            month = current_month

        else:
            try:
                print("\nExample input: 10")
                month = int(input("Month: "))

            except ValueError:
                print("Invalid input. Please enter an integer.")
                exit()

    else:
        try:
            print("\nExample input: 2023")
            year = int(input("Year: "))

            print("\nExample input: 10")
            month = int(input("Month: "))

        except ValueError:
            print("Invalid input. Please enter an integer.")
            exit()

    try:
        max_day = check_month_days(month, year)
        day = 0

        while day <= 0 or day > max_day:
            print("\nExample format: 16")
            day = int(input("Enter the day: "))

            if day > max_day:
                print(f"Highest value in {month_to_text(month)} is {max_day}")

            # Catch empty values
            elif day == "" or day is None:
                day = 0

        print("\nExample format: 6:05pm")
        time = input("Enter the time: ")

        time = time.split(':')  # Creates an array
        hour = int(time[0])  # Isolate the hour
        minute = int(time[1][0:2])  # Snag minutes
        time_of_day = str(time[1][2:4])  # Grab time of day

        hour = mil_time(hour, time_of_day)  # Convert to 24-hour

    except (ValueError):
        print("Invalid input. Please enter an integer")
        exit()

    return time_to_epoch(year, month, day, hour, minute)


def check_month_days(month, year):
    """
    Checks how many days are in the given month.
    
    :param month: The integer month of the year to check.
    :type month: int
    :param year: The year of the date that is being checked.
    :type year: int
    :return: Returns the amount of days in a month.
    :rtype: int
    """
    if ((month == 2) and ((year % 4 == 0) or ((year % 100 == 0)
                                              and (year % 400 == 0)))):
        return 29

    elif (month == 2):
        return 28

    elif (month == 1 or month == 3 or month == 5 or month == 7 or month == 8
          or month == 10):
        return 31

    else:
        return 30


def mil_time(hour, time_of_day):
    """
    Converts 12-hour time format to 24-hour format.

    :param hour: The hour in 12-hour format to be converted to 24-hour.
    :type hour: int
    :param time_of_day: The time of day as either 'am' or 'pm'
    :type time_of_day: str
    :return: Returns the hour in 24-hour time formatting
    :rtype: int
    """
    if (time_of_day == "pm"):
        hour += 12

    return hour


def time_to_epoch(year, month, day, hour, minute):
    """Converts given integers into a UNIX timestamp"""
    py_time = datetime.datetime(year, month, day, hour, minute)

    unix_timestamp = int(py_time.timestamp())

    return unix_timestamp


def get_link(timestamp, camera_id, org_id=ORG_ID, api_key=API_KEY):
    """
    Prints a link to a given camera with footage to the given time.
    
    :param timestamp: The UNIX timestamp for the desired footage.
    :type timestamp: int
    :param camera_id: The camera ID of the device to pull footage from.
    :type camera_id: str
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: None
    :rtype: None
    """
    headers = {
        'accept': 'application/json'
    }

    params = {
        'org_id': org_id,
        'camera_id': camera_id,
        'timestamp': timestamp,
        'x-api-key': api_key
    }

    response = requests.get(URL, headers=headers, params=params, timeout=5)

    print(response)


def run():
    """Allows you to run the full program if being imported"""
    get_link(ask_time, str(input("Camera ID: ")))


# Checks if the program is being ran directly or imported
if __name__ == "__main__":
    run()
