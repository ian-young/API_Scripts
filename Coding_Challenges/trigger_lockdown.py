"""
Author: Ian Young
Purpose: Opens lockdowns both literally and figuratively
"""

# Import essential libraries
import logging
from os import getenv

import requests
from dotenv import load_dotenv

import QoL.custom_exceptions as custom_exceptions
from QoL.verkada_totp import generate_totp

log = logging.getLogger()
log.setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Static URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"

load_dotenv()  # Load credentials file

# User logging credentials
USERNAME = getenv("")
PASSWORD = getenv("")
ORG_ID = getenv("")

LOCKDOWN_ID = "9884e9b2-1871-4aaf-86d7-0dc12b4ff024"  # String or list


##############################################################################
##############################  Authentication  ##############################
##############################################################################


def login_and_get_tokens(login_session, username, password, org_id):
    """
    Initiates a Command session with the given user credentials and Verkada
    organization ID.

    :param login_session: The session to use when authenticating.
    :type login_session: requests.Session
    :param username: A Verkada user's username to be used during the login.
    :type username: str, optional
    :param password: A Verkada user's password used during the login process.
    :type password: str, optional
    :param org_id: The Verkada Org ID that is being logged into.
    :type org_id: str, optional
    :return: Will return the csrf_token of the session that has been initiated
    along with the user token for the session and the user's id.
    :rtype: String, String, String
    """
    # Prepare login data
    login_data = {
        "email": username,
        "password": password,
        "otp": generate_totp(getenv("lab_totp")),
        "org_id": org_id,
    }

    try:
        # Request the user session
        response = login_session.post(LOGIN_URL, json=login_data)
        response.raise_for_status()

        # Extract relevant information from the JSON response
        json_response = response.json()
        session_csrf_token = json_response.get("csrfToken")
        session_user_token = json_response.get("userToken")
        session_user_id = json_response.get("userId")

        return session_csrf_token, session_user_token, session_user_id

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Log in"
        ) from e


def logout(logout_session, x_verkada_token, x_verkada_auth, org_id=ORG_ID):
    """
    Logs the Python script out of Command to prevent orphaned sessions.

    :param logout_session: The session to use when authenticating.
    :type logout_session: requests.Session
    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    """
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "x-verkada-organization": org_id,
    }

    body = {"logoutCurrentEmailOnly": True}
    try:
        response = logout_session.post(LOGOUT_URL, headers=headers, json=body)
        response.raise_for_status()

        log.info("Logging out.")

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Logout"
        ) from e

    finally:
        logout_session.close()


##############################################################################
#################################  Requests  #################################
##############################################################################


def trigger_lockdown(
    lockdown_session, x_verkada_token, x_verkada_auth, usr, org_id, lockdown_id
):
    """
    Triggers the given lockdown(s) inside of Verkada Command with a valid Command
    user session. The lockdown trigger event will appear as a remote trigger in the
    audit logs.

    :param lockdown_session: The session to use when authenticating.
    :type lockdown_session: requests.Session
    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkada organization.
    :type usr: str
    :param org_id: The Verkada organization ID of the target org.
    :type org_id: str
    :param lockdown_id: The id of the lockdown to trigger.
    :type lockdown_id: str, list[str]
    """
    url = f"https://vcerberus.command.verkada.com/organizations/{org_id}/lockdowns/trigger"
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr,
    }
    try:
        # Check to see if a list of lockdowns was given
        log.debug("Checking if a list was provided.")

        if isinstance(lockdown_id, list):
            log.debug("List provided -> Checking if list is iterable.")

            if hasattr(lockdown_id, "__iter__"):
                log.debug(
                    "List provided -> list is iterable -> attempting triggers."
                )

                for target in lockdown_id:
                    body = {"lockdownId": target}

                    log.debug("triggering lockdown: %s.", target)
                    response = lockdown_session.post(
                        url, headers=headers, json=body
                    )
                    response.raise_for_status()

            else:
                log.critical("List is not iterable.")

        # Run for a single lockdown
        else:
            body = {"lockdownId": lockdown_id}

            log.debug("triggering %s.", lockdown_id)
            response = lockdown_session.post(url, headers=headers, json=body)
            response.raise_for_status()

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Lockdown"
        ) from e


if __name__ == "__main__":
    try:
        with requests.Session() as session:
            log.debug("Retrieving credentials.")
            csrf_token, user_token, user_id = login_and_get_tokens(
                session, USERNAME, PASSWORD, ORG_ID
            )

            if csrf_token and user_token and user_id:
                log.debug("Credentials retrieved.")
                trigger_lockdown(
                    session,
                    csrf_token,
                    user_token,
                    user_id,
                    ORG_ID,
                    LOCKDOWN_ID,
                )
                log.debug("All lockdowns triggered.")

            else:
                log.warning("Did not receive the necessary credentials.")

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")

    finally:
        logout(session, csrf_token, user_token)
        session.close()
