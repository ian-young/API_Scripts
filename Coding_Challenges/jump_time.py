"""
Author: Ian Young
Purpose: To provide a link to a camera at a certain time
to speed up the process of searching for footage.
"""

# Import essential libraries
import datetime

import requests

ORG_ID = ""
API_KEY = ""
URL = "https://api.verkada.com/cameras/v1/footage/link"


def month_to_text(month):
    """
    Takes an integer and convert it to text for the correlated month

    :param month: The integer value of a month.
    :type month: int
    :return: The string of a month name.
    :rtype: str
    """
    months = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    }

    return months[int(month)]


def ask_time():
    """
    Asks the user for a date and returns an epoch timestamp

    :return: Epoch timestamp of a prompted date.
    :rtype: int
    """
    # Pre-define variables that may be auto-filled
    year = None
    month = None
    day = None
    hour = None
    minute = None
    answer = None

    # Load current values
    current_year = int(datetime.datetime.now().date().strftime("%Y"))
    current_month = int(datetime.datetime.now().date().strftime("%m"))
    month_text = month_to_text(current_month)

    while answer not in ["y", "n"]:
        print(f"Is the footage from {current_year}?")
        answer = input("(y/n) ").strip().lower()

    if answer == "y":
        year = current_year
        answer = None  # reset

        while answer not in ["y", "n"]:
            print(f"Is the footage from {month_text}?")
            answer = input("(y/n) ").strip().lower()

        if answer == "y":
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

        time = time.split(":")  # Creates an array
        hour = int(time[0])  # Isolate the hour
        minute = int(time[1][:2])
        time_of_day = str(time[1][2:4])  # Grab time of day

        hour = mil_time(hour, time_of_day)  # Convert to 24-hour

    except ValueError:
        print("Invalid input. Please enter an integer")
        exit()

    return time_to_epoch(year, month, day, hour, minute)


def check_month_days(month, year):
    """
    Checks how many days are in the given month

    :param month: The month value to be checking.
    :type month: int
    :param year: They year to check against.
    :type year: int
    :return: Returns how many days are in the month.
    :rtype: int
    """
    if (month == 2) and (
        (year % 4 == 0) or ((year % 100 == 0) and (year % 400 == 0))
    ):
        return 29

    elif month == 2:
        return 28

    elif month in [1, 3, 5, 7, 8, 10]:
        return 31

    else:
        return 30


def mil_time(hour, time_of_day):
    """
    Converts 12-hour time to 24-hour

    :param hour: The 12-hour value to convert to 24-hours.
    :type hour: int
    :param time_of_day: whether the time is 'am' or 'pm'
    :type time_of_day: str
    :return: The hour in 24-hour format.
    :rtype: int
    """
    if time_of_day == "pm":
        hour += 12

    return hour


def time_to_epoch(year, month, day, hour, minute):
    """
    Converts given integers into a UNIX timestamp

    :param year: The year to to be converted to epoch time.
    :type year: int
    :param month: The month to to be converted to epoch time.
    :type month: int
    :param day: The day to to be converted to epoch time.
    :type day: int
    :param hour: The hour to to be converted to epoch time.
    :type hour: int
    :param minute: The minute to to be converted to epoch time.
    :type minute: int
    :return: An epoch timestamp in milliseconds.
    :rtype: int
    """
    py_time = datetime.datetime(year, month, day, hour, minute)

    return int(py_time.timestamp())


def get_link(timestamp, camera_id, org_id=ORG_ID, api_key=API_KEY):
    """
    Prints a link to a given camera with footage to the given time.

    :param timestamp: An epoch timestamp formatted in milliseconds.
    :type timestamp: int
    :param camera_id: A Verkada camera device ID.
    :type camera_id: str
    :param org_id: The organization ID of which the camera resides in.
    :type org_id: optional, str
    :param api_key: The API key used to authenticate to the Verkada org.
    :type api_key: optional, str
    """
    headers = {"accept": "application/json"}

    params = {
        "org_id": org_id,
        "camera_id": camera_id,
        "timestamp": timestamp,
        "x-api-key": api_key,
    }

    response = requests.get(URL, headers=headers, params=params, timeout=5)

    print(response)


def run():
    """
    Allows you to run the full program if being imported

    Returns:
        None
    """
    get_link(ask_time, str(input("Camera ID: ")))


# Checks if the program is being ran directly or imported
if __name__ == "__main__":
    run()
