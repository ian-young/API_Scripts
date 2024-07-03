"""
Author: Ian Young
Purpose: Remove entries from a data file that are older than 24 hours. This
will help keep data relevant.
"""
# Import essential libraries
import re
from datetime import datetime, timedelta

LOG_FILE_PATH = (
    "/Users/ian.young/Documents/.scripts/Python/API_Scripts/endpoint_data.log"
)


def parse_entry(entry):
    """
    Parse the data of data given a file.

    :param entry: The text read line-by-line in a file.
    :type entry: str
    :return: The formatted time for the entry file.
    :rtype: datetime
    """
    # Use regular expression to extract the time string in the entry
    time_match = re.search(r"(\d{2}/\d{2} \d{2}:\d{2}:\d{2})", entry)
    if time_match:
        time_str = time_match.group(1)
        # Set the year to the current year
        current_year = datetime.now().year
        return datetime.strptime(
            f"{current_year} {time_str}", "%Y %m/%d %H:%M:%S"
        )


def filter_entries(old_entries):
    """
    Filters any entry older than 24 hours.

    :param old_entries: Entries from a data file that may be older than 24h.
    :type old_entries: list
    :return: Only entries that are 24 hours old or newer.
    :rtype: list
    """
    new_entries = []
    current_time = datetime.now()

    include_entry = False

    for entry in old_entries:
        execution_time = parse_entry(entry)
        if execution_time:
            time_difference = current_time - execution_time

            # Check if the entry is within the last 24 hours
            if time_difference < timedelta(days=1):
                include_entry = True
                new_entries.append(entry)
            else:
                include_entry = False

        elif include_entry:
            new_entries.append(entry)

    return new_entries


if __name__ == "__main__":
    # Read the entries from the file
    with open(LOG_FILE_PATH, "r", encoding="utf-8") as file:
        entries = file.readlines()

    # Filter the entries
    filtered_entries = filter_entries(entries)

    # Overwrite the original file with the filtered entries
    with open(LOG_FILE_PATH, "w", encoding="utf-8") as file:
        file.writelines(filtered_entries)
