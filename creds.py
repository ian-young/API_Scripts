from getpass import getpass
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)


def get_password():
    try:
        return getpass("Enter your password: ")
    except KeyboardInterrupt:
        logging.info("\nKeyboard interrupt detected. Exiting...")
