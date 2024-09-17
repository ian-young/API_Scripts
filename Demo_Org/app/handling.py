"""
Author: Ian Young
Purpose: Hold small miscellaneous functions for calculations, running boards, and house keeping.
"""

import threading
from time import sleep
from typing import Any, List

import requests

from tools import log, APIThrottleException, APIExceptionHandler

from .config import RequestConfig

try:
    from RPi import GPIO  # type: ignore

    RETRY_PIN = 11
    POI_PIN = 11
    FAIL_PIN = 13
    LPOI_PIN = 13
    RUN_PIN = 7
    SUCCESS_PIN = 15

    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(RUN_PIN, GPIO.OUT)
        GPIO.setup(RETRY_PIN, GPIO.OUT)
        GPIO.setup(FAIL_PIN, GPIO.OUT)
        if SUCCESS_PIN:
            GPIO.setup(SUCCESS_PIN, GPIO.OUT)
    except RuntimeError:
        GPIO = None
        log.debug("GPIO Runtime error")
except ImportError:
    GPIO = None
    log.debug("RPi.GPIO is not available. Running on a non-Pi platform")


def clean_list(messy_list: List[Any]) -> List[Any]:
    """
    Removes any None values from error codes

    :param list: The list to be cleaned.
    :type list: list
    :return: A new list with None values removed.
    :rtype: list
    """
    return [value for value in messy_list if value is not None]


def flash_led(pin: int, local_stop_event: threading.Event, speed: int):
    """
    Flashes an LED that is wired into the GPIO board of a raspberry pi for
    the duration of work.

    :param pin: target GPIO pin on the board.
    :type pin: int
    :param local_stop_event: Thread-local event to indicate when the program's
    work is done and the LED can stop flashing.
    :type local_stop_event: threading.Event
    :param speed: How long each flash should last in seconds.
    :type failed: int
    :return: None
    :rtype: None
    """
    while not local_stop_event.is_set():
        GPIO.output(pin, True)
        sleep(speed)
        GPIO.output(pin, False)
        sleep(speed * 2)


def perform_request(config: RequestConfig, local_data, max_retries):
    """Performs an HTTP DELETE request with retry logic for handling
    throttling.

    This function attempts to send a DELETE request to a specified URL,
    handling various response statuses and implementing a retry mechanism
    in case of throttling or timeouts.

    Args:
        config: An object containing the request configuration, including
            URL, headers, and parameters.
        local_data: An object containing local state, including the retry
            delay.
        max_retries: The maximum number of retry attempts for the request.

    Returns:
        The response object from the DELETE request.

    Raises:
        APIExceptionHandler: If a request fails due to an exception.
        APIThrottleException: If the API is throttled after the maximum
            number of retries.
    """
    for _ in range(max_retries):
        try:
            response = requests.delete(
                config.url,
                headers=config.headers,
                params=config.params,
                timeout=5,
            )

            if response.status_code == 429:
                handle_api_throttle(config, local_data)

            if response.status_code == 504:
                log.warning("%s Request timed out.", str(config.print_name))
            elif response.status_code == 400:
                log.warning(
                    "%s Contact support: endpoint failure",
                    str(config.print_name),
                )
            elif response.status_code != 200:
                log.error(
                    "An error has occurred. Status code %s",
                    response.status_code,
                )

            return response

        except requests.exceptions.Timeout:
            log.warning("Request timed out.")
        except requests.exceptions.RequestException as e:
            log.error("Request failed: %s", str(e))
            raise APIExceptionHandler(e, response, "Request failed -") from e

        sleep(local_data.RETRY_DELAY)  # Delay between retries

    raise APIThrottleException("API throttled after multiple retries")


def handle_api_throttle(config: RequestConfig, local_data):
    """Handles API throttling by logging the event and implementing a
    backoff.

    This function logs the occurrence of API throttling and pauses
    execution for a specified backoff period to comply with the API's rate
    limits.

    Args:
        config: An object containing the request configuration, including
            the backoff time and arguments.
        local_data: An object containing local state relevant to the
            throttling event.

    Returns:
        None
    """
    # Implement the API throttle handling logic here
    log.info(
        "Handling API throttle for %s with args %s",
        config.print_name(*config.args),
        local_data,
    )
    sleep(config.backoff)
