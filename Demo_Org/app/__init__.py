"""Streamline imports"""

import threading

from .handling import GPIO, RUN_PIN
from .people import run_people
from .plates import run_plates


class PurgeManager:
    """
    Manages the state of API call count and provides thread-safe methods
    to control and monitor the call limit.

    Attributes:
        call_count (int): The current number of API calls made.
        call_count_lock (threading.Lock): A lock to ensure thread-safe access to call_count.
        call_count_limit (int): The maximum number of API calls allowed.
    """

    def __init__(self, call_count_limit=300):
        """
        Initializes the PurgeManager with a specified call count limit.

        Args:
            call_count_limit (int): The maximum number of API calls allowed.
                                    Defaults to 300.
        """
        self.call_count = 0
        self.call_count_lock = threading.Lock()
        self.call_count_limit = call_count_limit

    def increment_call_count(self):
        """
        Increments the call count by one in a thread-safe manner.

        Returns:
            int: The updated call count after incrementing.
        """
        with self.call_count_lock:
            self.call_count += 1
            return self.call_count

    def should_stop(self):
        """
        Checks if the current call count has reached or exceeded the limit.

        Returns:
            bool: True if the call count has reached or exceeded the limit, False otherwise.
        """
        with self.call_count_lock:
            return self.call_count >= self.call_count_limit

    def reset_call_count(self):
        """
        Resets the call count to zero in a thread-safe manner.
        """
        with self.call_count_lock:
            self.call_count = 0
