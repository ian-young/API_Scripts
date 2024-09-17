"""
Author: Ian Young
Purpose: Run threads on a clock to avoid triggering API rate limit warnings.
"""

import threading
import time

from datetime import datetime
from typing import List
from tqdm import tqdm

from tools import log


class RateLimiter:
    """
    The purpose of this class is to limit how fast multi-threaded actions are
    created to prevent hitting the API limit.
    """

    def __init__(
        self, rate_limit: int, max_events_per_sec: int = 5, pacing: int = 1
    ):
        """
        Initialization of the rate limiter.

        :param rate_limit: The value of how many threads may be made each sec.
        :type rate_limit: int
        :param max_events_per_sec: Maximum events allowed per second.
        :type: int, optional
        :param pacing: Sets the interval of the clock in seconds.
        :type pacing: int, optional
        :return: None
        :rtype: None
        """
        self.rate_limit = rate_limit
        self.lock = threading.Lock()  # Local lock to prevent race conditions
        self.max_events_per_sec = max_events_per_sec
        self.pacing = pacing
        self.start_time: float = 0
        self.event_count = 0

    def acquire(self) -> bool:
        """
        States whether or not the program may create new threads or not.

        :return: Boolean value stating whether new threads may be made or not.
        :rtype: bool
        """
        with self.lock:
            current_time = time.time()  # Define current time

            if self.start_time == 0:
                self.start_time = current_time
                self.event_count = self.pacing
                return True

            elapsed_since_start = current_time - self.start_time

            if (
                elapsed_since_start < self.pacing / self.rate_limit
                and self.event_count < self.max_events_per_sec
            ):
                self.event_count += 1
            elif elapsed_since_start >= self.pacing / self.rate_limit:
                self.start_time = current_time
                self.event_count = 2
            else:
                remaining_time = self.pacing - (current_time - self.start_time)
                time.sleep(remaining_time)

            return True

    def reset(self):
        """
        Resets the rate limiter to its initial state.
        """
        with self.lock:
            self.start_time = 0
            self.event_count = 0

    def get_status(self) -> dict:
        """
        Returns the current status of the rate limiter.

        :return: A dictionary with current status information.
        :rtype: dict
        """
        with self.lock:
            return {
                "rate_limit": self.rate_limit,
                "max_events_per_sec": self.max_events_per_sec,
                "pacing": self.pacing,
                "start_time": self.start_time,
                "event_count": self.event_count,
            }

    def set_rate_limit(self, rate_limit: int):
        """
        Sets a new rate limit for the rate limiter.

        :param rate_limit: The new rate limit value.
        :type rate_limit: int
        """
        with self.lock:
            self.rate_limit = rate_limit

    def set_max_events_per_sec(self, max_events_per_sec: int):
        """
        Sets a new maximum events per second value.

        :param max_events_per_sec: The new maximum events per second value.
        :type max_events_per_sec: int
        """
        with self.lock:
            self.max_events_per_sec = max_events_per_sec


def run_thread_with_rate_limit(
    threads: List[threading.Thread], description: str, rate_limit: int = 5
):
    """
    Run a thread with rate limiting.

    :param threads: The threads to be ran with rate limiting
    :type threads: List[threading.Thread]
    :param rate_limit: How many threads may be ran per second.
    :type rate_limit: int
    :return: The thread that was created and ran
    :rtype: thread
    """
    limiter = RateLimiter(rate_limit=rate_limit)
    progress_bar = tqdm(
        total=len(threads) * 2, desc=f"Processing {description} threads"
    )

    def run_thread(thread):
        limiter.acquire()
        log.debug(
            "Starting thread %s at time %s",
            thread.name,
            datetime.now().strftime("%H:%M:%S"),
        )
        thread.start()

    for thread in threads:
        run_thread(thread)
        progress_bar.update(1)

    for thread in threads:
        thread.join()
        progress_bar.update(1)

    progress_bar.close()
