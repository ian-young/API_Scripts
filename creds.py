"""
Author: Ian Young
Purpose: Securely ask for credentials inside of code.
"""
# Import essential libraries
from getpass import getpass
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)


def get_password():
    """
    Will securely prompt for credentials inside the operating terminal.
    """
    try:
        return getpass("Enter your password: ")
    except KeyboardInterrupt:
        logging.info("\nKeyboard interrupt detected. Exiting...")
