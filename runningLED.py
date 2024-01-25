import time
import logging

log = logging.getLogger()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s"
)

try:
    import RPi.GPIO as GPIO  # type: ignore

    gpio_pin = 15
    
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
    #for _ in range(0, 9):
    #   time.sleep(1)
    flashLED(gpio_pin, 5)



def flashLED(pin, count):
    for _ in (0, count):
        log.debug("Flash on")
        GPIO.output(pin, True)
        time.sleep(0.5)
        GPIO.output(pin, False)
        time.sleep(0.5)
        log.debug("Flash off")


if GPIO:
    GPIO.output(gpio_pin, True)
    log.debug("LED on.")
    work()
    GPIO.output(gpio_pin, False)
    log.debug("LED off.")
    GPIO.cleanup()
else:
    log.debug("Skipping GPIO operations. GPIO unavailable.")

