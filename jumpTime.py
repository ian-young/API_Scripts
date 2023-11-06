# Author: Ian Young
# Purpose: To provide a link to a camera at a certain time
# to speed up the process of searching for footage

import requests
import datetime

ORG_ID = ""
API_KEY = ""
URL = "https://api.verkada.com/cameras/v1/footage/link"


def monthToText(month):
    """Takes an integer and conver it to text for the correlated month"""
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


def askTime():
    """Asks the user for a date and returns an epoch timestamp"""
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
    month_text = monthToText(current_month)

    while answer not in ['y', 'n']:
        print(f"Is the footage from {current_year}?")
        answer = input("(y/n) ").strip().lower()

    if (answer == 'y'):
        year = current_year
        answer = None  # reset

        while answer not in ['y', 'n']:
            print(f"Is the footage from {month_text}?")
            answer = input("(y/n) ").strip().lower()

        if (answer == 'y'):
            month = current_month

        else:
            try:
                print("\nExample input: 10")
                month = int(input("Month: "))

            except (ValueError):
                print("Invalid input. Please enter an integer.")
                exit()

    else:
        try:
            print("\nExample input: 2023")
            year = int(input("Year: "))

            print("\nExample input: 10")
            month = int(input("Month: "))

        except (ValueError):
            print("Invalid input. Please enter an integer.")
            exit()

    try:
        max_day = checkMonthDays(month, year)
        day = 0

        while day <= 0 or day > max_day:
            print("\nExample format: 16")
            day = int(input("Enter the day: "))

            if day > max_day:
                print(f"Highest value in {monthToText(month)} is {max_day}")

            # Catch empty values
            elif day == "" or day == None:
                day = 0

        print("\nExample format: 6:05pm")
        time = input("Enter the time: ")

        time = time.split(':')  # Creates an array
        hour = int(time[0])  # Isolate the hour
        minute = int(time[1][0:2])  # Snag minutes
        time_of_day = str(time[1][2:4])  # Grab time of day

        hour = milTime(hour, time_of_day)  # Convert to 24-hour

    except (ValueError):
        print("Invalid input. Please enter an integer")
        exit()

    return timeToEpoch(year, month, day, hour, minute)


def checkMonthDays(month, year):
    """Checks how many days are in the given month"""
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


def milTime(hour, time_of_day):
    """Converts 12-hour time to 24-hour"""
    if (time_of_day == "pm"):
        hour += 12

    return hour


def timeToEpoch(year, month, day, hour, minute):
    """Converts given integers into a UNIX timestamp"""
    py_time = datetime.datetime(year, month, day, hour, minute)

    unix_timestamp = int(py_time.timestamp())

    return unix_timestamp


def getLink(timestamp, camera_ID, org_id=ORG_ID, api_key=API_KEY):
    """Prints a link to a given camera with footage to the given time"""
    headers = {
        'accept': 'application/json'
    }

    params = {
        'org_id': org_id,
        'camera_id': camera_ID,
        'timestamp': timestamp,
        'x-api-key': api_key
    }

    response = requests.get(URL, headers=headers, params=params)

    print(response)


def run():
    """Allows you to run the full program if being imported"""
    getLink(askTime, str(input("Camera ID: ")))

    # Uncomment the lines below to manually enter the org id and api key
    # getLink(askTime, str(input("Camera ID: ")), str(input("Org ID: ")), \
    # str(input("API Key: ")))


# Checks if the program is being ran directly or imported
if __name__ == "__main__":
    run()
