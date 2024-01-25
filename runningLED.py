import time
import logging

log = logging.getLogger()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s"
)

try:
    import RPi.GPIO as GPIO  # type: ignore

    gpio_pin = 7
    
    try:
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(gpio_pin, GPIO.OUT)
        GPIO.setwarnings(False)
    except RuntimeError:
        GPIO = None
        GPIO.setup(gpio_pin, GPIO.OUT)
        log.debug("Runtime error")
except ImportError:
    GPIO = None
    log.critical("RPi.GPIO is not availbale. Running on a non-Pi platform")


def work():
    log.debug("Running work function")
    for _ in range(0, 5):
        time.sleep(1)

if GPIO:
    GPIO.output(gpio_pin, True)
    log.debug("LED on.")
    work()
    GPIO.output(gpio_pin, False)
    log.debug("LED off.")
    GPIO.cleanup()
else:
    log.debug("Skipping GPIO operations. GPIO unavailable.")

