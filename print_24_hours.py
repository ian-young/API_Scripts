"""
Author: Ian Young
Purpose: Print the past 24 hour's worth of endpoint data. To be used by
tryEndpoints.py.
"""
# Import essential libraries
import re
from datetime import datetime, timedelta


def parse_entry(entry):
    """
    Parse the data of data given a file.

    :param entry: The text read line-by-line in a file.
    :type entry: str
    :return: The formatted time for the entry file.
    :rtype: datetime
    """
    if time_match := re.search(r"(\d{2}/\d{2} \d{2}:\d{2}:\d{2})", entry):
        time_str = time_match[1]
        # Set the year to the current year
        current_year = datetime.now().year
        return datetime.strptime(
            f"{current_year} {time_str}", "%Y %m/%d %H:%M:%S"
        )


def main():
    """Driver function. Will read only the past 24-hour's worth od data."""
    # Specify your log file path
    log_file_path = "./endpoint_data.log"

    # Read the file
    with open(log_file_path, "r", encoding="utf-8") as file:
        entries = file.readlines()

    # Get the current time
    current_time = datetime.now()

    # Flag to determine whether to print an entry
    print_entry = False

    # Iterate through entries and check if they are within the last 24 hours
    for entry in entries:
        if "Time of execution" in entry:
            if execution_time := parse_entry(entry):
                time_difference = current_time - execution_time

                # Check if the entry is within the last 24 hours
                if time_difference < timedelta(days=1):
                    print_entry = True
                    print(entry.strip())  # Print the "Time of execution" entry
                else:
                    print_entry = False
        elif print_entry:
            print(entry.strip())


# Checks if the file is being imported or not
if __name__ == "__main__":
    main()
