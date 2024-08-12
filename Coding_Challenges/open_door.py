"""
Author: Ian Young
Purpose: Opens doors both literally and figuratively.
"""

# Import essential libraries
import logging
from os import getenv

import requests
from dotenv import load_dotenv

from QoL import login_and_get_tokens, logout, custom_exceptions

load_dotenv()  # Load credentials file

log = logging.getLogger()
log.setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Static URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"

# User logging credentials
USERNAME = getenv("")
PASSWORD = getenv("")
ORG_ID = getenv("")

VIRTUAL_DEVICE = "5eff4677-974d-44ca-a6ba-fb7595265e0a"  # String or list


def unlock_door(unlock_session, x_verkada_token, x_verkada_auth, usr, door):
    """
    Unlocks the given door(s) inside of Verkada Command with a valid Command
    user session. The door unlock event will appear as a remote unlock in the
    audit logs.

    :param unlock_session: The session to use when unlocking the door.
    :type unlock_session: requests.Session
    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkada organization.
    :type usr: str
    """
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr,
    }
    try:
        # Check to see if a list of doors was given
        log.debug("Checking if a list was provided.")

        if isinstance(door, list):
            log.debug("List provided -> Checking if list is iterable.")

            if hasattr(door, "__iter__"):
                log.debug(
                    "List provided -> list is iterable -> attempting unlocks."
                )

                for target in door:
                    url = f"https://vcerberus.command.verkada.com/access/v2/\
user/virtual_device/{target}/unlock"

                    log.debug("Unlocking virtual device: %s.", target)
                    response = unlock_session.post(url, headers=headers)
                    response.raise_for_status()

            else:
                log.critical("List is not iterable.")

        # Run for a single door
        else:
            log.debug("Unlocking %s.", door)
            url = f"https://vcerberus.command.verkada.com/access/v2/user/\
virtual_device/{door}/unlock"
            response = unlock_session.post(url, headers=headers)
            response.raise_for_status()

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Unlock Door"
        ) from e


if __name__ == "__main__":
    with requests.Session() as session:
        try:
            log.debug("Retrieving credentials.")
            if USERNAME and PASSWORD and ORG_ID:
                csrf_token, user_token, user_id = login_and_get_tokens(
                    session, USERNAME, PASSWORD, ORG_ID
                )

                if csrf_token and user_token and user_id:
                    log.debug("Credentials retrieved.")
                    unlock_door(
                        session,
                        csrf_token,
                        user_token,
                        user_id,
                        VIRTUAL_DEVICE,
                    )
                    log.debug("All door(s) unlocked.")

            else:
                log.warning("Did not receive the necessary credentials.")

        except KeyboardInterrupt:
            log.warning("Keyboard interrupt detected. Exiting...")

        finally:
            if ORG_ID and "csrf_token" in locals():
                logout(session, csrf_token, user_token, ORG_ID)
            session.close()
