"""
Author: Ian Young
Purpose: This script is used to log in and log out of a Command account.
"""

# Import essential libraries
import logging

import requests
from QoL.api_endpoints import LOGIN, LOGOUT
from QoL.verkada_totp import generate_totp

# Import custom exceptions to save space
import QoL.custom_exceptions as custom_exceptions

# Set up the logger
log = logging.getLogger()
LOG_LEVEL = logging.ERROR
log.setLevel(LOG_LEVEL)
logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s: %(message)s")


def login_and_get_tokens(login_session, username, password, totp, org_id):
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
    :param totp: The TOTP secret used for 2FA
    :type totp: str
    :return: Will return the csrf_token of the session that has been initiated
    along with the user token for the session and the user's id.
    :rtype: String, String, String
    """
    # Prepare login data
    login_data = {
        "email": username,
        "password": password,
        "otp": generate_totp(totp),
        "org_id": org_id,
    }

    try:
        # Request the user session
        log.debug("Requesting session.")
        response = login_session.post(LOGIN, json=login_data)
        response.raise_for_status()
        log.debug("Session opened.")

        # Extract relevant information from the JSON response
        log.debug("Parsing JSON response.")
        json_response = response.json()
        session_csrf_token = json_response.get("csrfToken")
        session_user_token = json_response.get("userToken")
        session_user_id = json_response.get("userId")
        log.debug("Response parsed. Returning values.")

        return session_csrf_token, session_user_token, session_user_id

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Log in"
        ) from e


def logout(logout_session, x_verkada_token, x_verkada_auth, org_id):
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
        "X-Verkada-Organization-Id": org_id,
        "X-Verkada-Token": x_verkada_token,
        "X-Verkada-User-Id": x_verkada_auth,
        "content-type": "application/json"
    }

    body = {"logoutCurrentEmailOnly": True}
    try:
        response = logout_session.post(LOGOUT, headers=headers, json=body)
        response.raise_for_status()

        log.info("Logging out.")

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Logout"
        ) from e

    finally:
        logout_session.close()
