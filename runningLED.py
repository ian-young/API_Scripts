import time
import logging

log = logging.getLogger()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s"
)

try:
    import RPi.GPIO as GPIO  # type: ignore
    if GPIO.gpio_function(7) != GPIO.out:
        GPIO.setup(7, GPIO.OUT)
except ImportError:
    GPIO = None
    log.critical("RPi.GPIO is not availbale. Running on a non-Pi platform")


def work():
    log.debug("Running work function")
    for _ in range(0, 5):
        time.sleep(1)


GPIO.output(7, True)
log.debug("LED on.")
work()
GPIO.output(7, False)
log.debug("LED off.")
