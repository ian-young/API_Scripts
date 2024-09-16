"""
Author: Ian Young
Purpose: Hold configuration settings and constants used across the project.
"""

import os
from dataclasses import dataclass
from typing import List

# Import environment variables
ORG_ID = os.environ.get("slc_id")
API_KEY = os.environ.get("slc_key")

# Set the full name for which plates are to be persistent
PERSISTENT_PLATES: List[str] = sorted([])
PERSISTENT_PERSONS: List[str] = sorted(["Parkour", "HQ Shoplifter"])
PERSISTENT_PID: List[str] = sorted(["751e9607-4617-43e1-9e8c-1bd439c116b6"])
PERSISTENT_LID: List[str] = sorted([])

# Set the full name for which users are to be persistent
PERSISTENT_USERS: List[str] = sorted(
    [
        "Ian Young",
        "Bruce Banner",
        "Jane Doe",
        "Tony Stark",
        "Ray Raymond",
        "John Doe",
    ]
)

# Set timeout for a 429
MAX_RETRIES = 10
DEFAULT_RETRY_DELAY = 0.25
BACKOFF = 0.25


@dataclass
class RequestConfig:
    """Represents the configuration for an API request.

    This class encapsulates the necessary parameters for making an API
    request, including the URL, headers, parameters, and a function for
    printing the name of the request along with its arguments.

    Args:
        url: The endpoint URL for the API request.
        headers: A dictionary of headers to include in the request.
        params: A dictionary of query parameters to include in the
            request.
        print_name: A callable function used to format the name of the
            request.
        args: A tuple of arguments to be passed to the print_name
            function.
        backoff: The backoff time in seconds to be used for retrying
            requests.

    Returns:
        None
    """

    url: str
    headers: dict
    params: dict
    print_name: callable
    args: tuple
    backoff: int
