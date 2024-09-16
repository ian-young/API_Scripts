"""
Author: Ian Young
Purpose: Print the past 24 hour's worth of endpoint data. To be used by
tryEndpoints.py.
"""

# Import essential libraries
from datetime import datetime, timedelta

from app.parse_entry import parse_entry


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
