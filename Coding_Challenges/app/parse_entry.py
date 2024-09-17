"""
Author: Ian Young
Purpose: Extract common code for importing.
"""

from re import search
from datetime import datetime


def parse_entry(entry):
    """
    Parse the data of data given a file.

    :param entry: The text read line-by-line in a file.
    :type entry: str
    :return: The formatted time for the entry file.
    :rtype: datetime
    """
    if time_match := search(r"(\d{2}/\d{2} \d{2}:\d{2}:\d{2})", entry):
        time_str = time_match[1]
        # Set the year to the current year
        current_year = datetime.now().year
        return datetime.strptime(
            f"{current_year} {time_str}", "%Y %m/%d %H:%M:%S"
        )
    return None
