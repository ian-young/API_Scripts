"""
Author: Ian Young
Purpose: Iterate through all archives that are visible to a user and delete
them. This is ONLY to be used to keep a given org clean. Extreme caution is
advised since the changes this script will make to the org cannot be undone
once made.
"""

# Import essential libraries
import logging
import time
from os import getenv

import requests
from dotenv import load_dotenv

import custom_exceptions
from verkada_totp import generate_totp

load_dotenv()  # Load credentials file

# Set final, global credential variables
USERNAME = getenv("")
PASSWORD = getenv("")
ORG_ID = getenv("")

# Set final, global URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"
ARCHIVE_URL = "https://vsubmit.command.verkada.com/library/export/list"

# Set up the logger
log = logging.getLogger()
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)


def login_and_get_tokens(login_session, username, password, org_id):
    """
    Initiates a Command session with the given user credentials and Verkada
    organization ID.

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
        raise custom_exceptions.APIExceptionHandler(e, response, "Log in") from e


def logout(logout_session, x_verkada_token, x_verkada_auth, org_id=ORG_ID):
    """
    Logs the Python script out of Command to prevent orphaned sessions.

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
        raise custom_exceptions.APIExceptionHandler(e, response, "Logout") from e

    finally:
        logout_session.close()


def read_verkada_camera_archives(
    archive_session, x_verkada_token, x_verkada_auth, usr, org_id=ORG_ID
):
    """
    Iterates through all Verkada archives that are visible to a given user.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkada organization.
    :type usr: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: An array of archived video export IDs.
    :rtype: list
    """
    body = {
        "fetchOrganizationArchives": True,
        "fetchUserArchives": True,
        "pageSize": 1000000,
        "organizationId": org_id,
    }

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr,
    }

    try:
        log.debug("Requesting archives.")
        response = archive_session.post(
            ARCHIVE_URL, json=body, headers=headers
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Archive IDs retrieved. Returning values.")

        return response.json().get("videoExports", [])

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        text = "Reading archives"
        raise custom_exceptions.APIExceptionHandler(e, response, text) from e


def count_archives(archive_library):
    """
    Counts how many elements are in a list.

    :param archive_library: A list of all Verkada archives
    :type archive_library: list
    """
    count = sum(1 for _ in archive_library)
    print(f"This org contains {count} archives.")


# Check if the script is being imported or ran directly
if __name__ == "__main__":
    try:
        start_time = time.time()

        # Start the user session
        with requests.Session() as session:
            csrf_token, user_token, user_id = login_and_get_tokens(
                session, USERNAME, PASSWORD, ORG_ID
            )

            if csrf_token and user_token and user_id:
                log.debug("Entering remove archives method.")
                count_archives(
                    read_verkada_camera_archives(
                        session, csrf_token, user_token, user_id
                    )
                )
                log.debug("Program completed successfully.")

            else:
                log.critical(
                    "No credentials were provided during the \
authentication process."
                )

        elapsed_time = time.time() - start_time
        log.info("Total time to complete %.2f", elapsed_time)
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Aborting...")

log.debug("Session closed. Exiting...")
