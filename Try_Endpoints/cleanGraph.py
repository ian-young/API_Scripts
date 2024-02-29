#!/usr/bin/env python
import re
from datetime import datetime, timedelta
from endpointTests import log_file_path as logfile

log_file_path = logfile

def parse_entry(entry):
    # Use regular expression to extract the time string in the entry
    time_match = re.search(r"(\d{2}/\d{2} \d{2}:\d{2}:\d{2})", entry)
    if time_match:
        time_str = time_match.group(1)
        # Set the year to the current year
        current_year = datetime.now().year
        return datetime.strptime(f"{current_year} {time_str}", "%Y %m/%d %H:%M:%S")

def filter_entries(entries):
    filtered_entries = []
    current_time = datetime.now()

    include_entry = False

    for entry in entries:
        execution_time = parse_entry(entry)
        if execution_time:
            time_difference = current_time - execution_time

            # Check if the entry is within the last 24 hours
            if time_difference < timedelta(days=1):
                include_entry = True
                filtered_entries.append(entry)
            else:
                include_entry = False

        elif include_entry:
            filtered_entries.append(entry)

    return filtered_entries

if __name__ == "__main__":
    # Read the entries from the file
    with open(log_file_path, "r") as file:
        entries = file.readlines()

    # Filter the entries
    filtered_entries = filter_entries(entries)

    # Overwrite the original file with the filtered entries
    with open(log_file_path, "w") as file:
        file.writelines(filtered_entries)
