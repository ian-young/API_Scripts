"""
Author: Ian Young
Purpose: Flash an LED on a Raspberry Pi when work is being done.
"""
import time
import logging

log = logging.getLogger()
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

try:
    import RPi.GPIO as GPIO  # type: ignore

    GPIO_PIN = 15

    try:
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(GPIO_PIN, GPIO.OUT)
        GPIO.setwarnings(False)
    except RuntimeError:
        GPIO = None
        GPIO.setup(GPIO_PIN, GPIO.OUT)
        log.debug("Runtime error")
except ImportError:
    GPIO = None
    log.critical("RPi.GPIO is not available. Running on a non-Pi platform")


def work():
    """Simulates work being done."""
    log.debug("Running work function")
    for _ in range(9):
        time.sleep(1)
    flash_led(GPIO_PIN, 5)


def flash_led(pin, count):
    """
    Toggle a GPIO pin on a Raspberry Pi.

    :param pin: The targeted pin on the board.
    :type pin: int
    :param count: How many times the pin should toggle.
    :type count: int
    """
    try:
        for _ in range(count):
            while True:
                flash(pin)
    except KeyboardInterrupt:
        print("\nExiting.")


def flash(pin):
    """
    Flash the LED connected to the specified GPIO pin by turning it on and
    off in 0.5-second intervals.

    Args:
        pin: The GPIO pin number to control the LED.

    Returns:
        None
    """
    log.debug("Flash on")
    GPIO.output(pin, True)
    time.sleep(0.5)
    GPIO.output(pin, False)
    time.sleep(0.5)
    log.debug("Flash off")


if GPIO:
    GPIO.output(GPIO_PIN, True)
    log.debug("LED on.")
    work()
    GPIO.output(GPIO_PIN, False)
    log.debug("LED off.")
    GPIO.cleanup()
else:
    log.debug("Skipping GPIO operations. GPIO unavailable.")
