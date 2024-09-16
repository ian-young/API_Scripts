#!/usr/bin/env python
"""
Author: Ian Young
Purpose: Remove any entries that are older than 24-hours UTC.
"""
import re
from datetime import datetime, timedelta
from endpoint_tests import log_file_path as logfile

log_file_path = logfile


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
    return None


def filter_entries(unfiltered_entries):
    """
    Filters any entry older than 24 hours.

    :param old_entries: Entries from a data file that may be older than 24h.
    :type old_entries: list
    :return: Only entries that are 24 hours old or newer.
    :rtype: list
    """
    changed_entries = []
    current_time = datetime.now()

    include_entry = False

    for entry in unfiltered_entries:
        if execution_time := parse_entry(entry):
            time_difference = current_time - execution_time

            # Check if the entry is within the last 24 hours
            if time_difference < timedelta(days=1):
                include_entry = True
                changed_entries.append(entry)
            else:
                include_entry = False

        elif include_entry:
            changed_entries.append(entry)

    return changed_entries


if __name__ == "__main__":
    # Read the entries from the file
    with open(log_file_path, "r", encoding="utf-8") as file:
        entries = file.readlines()

    # Filter the entries
    filtered_entries = filter_entries(entries)

    # Overwrite the original file with the filtered entries
    with open(log_file_path, "w", encoding="utf-8") as file:
        file.writelines(filtered_entries)
