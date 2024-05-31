"""
Author: Ian Young
Purpose: Serve as a template for logging in a user, performing an action,
and logging out.
"""
# Import essential libraries
import logging
import time
from os import getenv

import requests
from dotenv import load_dotenv

import custom_exceptions

load_dotenv()  # Load credentials file

# Set final, global credential variables
USERNAME = getenv("username")
PASSWORD = getenv("password")
ORG_ID = getenv("org_id")

# Set final, global URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"
ACTION_URL = ""  # Put the endpoint here

# Set up the logger
log = logging.getLogger()
log.setLevel(logging.DEBUG)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)


##############################################################################
                        #   Authentication   #
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
        raise custom_exceptions.APIExceptionHandler(e, response, "Log in")


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
        "x-verkada-orginization": org_id
    }

    body = {
        "logoutCurrentEmailOnly": True
    }
    try:
        response = logout_session.post(LOGOUT_URL, headers=headers, json=body)
        response.raise_for_status()

        log.info("Logging out.")

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(e, response, "Logout")

    finally:
        logout_session.close()


##############################################################################
                            #   Requests   #
##############################################################################


def command_action(action_session, x_verkada_token, x_verkada_auth,
                   usr, org_id=ORG_ID):
    """
    Perform an action in Command.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: An array of archived video export IDs.
    :rtype: list
    """
    # NOTE: Not all endpoints require a body.
    body = {
        "organizationId": org_id
    }

    # IMPORTANT: All endpoints will need this if not using apidocs.verkada.com
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    log.debug("Requesting camera data")

    try:
        response = action_session.post(ACTION_URL, json=body, headers=headers)
        response.raise_for_status()
        log.debug("-------")
        log.debug("Action completed.")

        return response.json()  # Return the endpoint response for computing.

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(e, response, "Log in")


##############################################################################
                                #   Main   #
##############################################################################


# Check if the script is being imported or ran directly
if __name__ == "__main__":

    with requests.Session() as session:
        start_run_time = time.time()  # Start timing the script
        try:
            # Initialize the user session.
            csrf_token, user_token, user_id = login_and_get_tokens(
                session,
                USERNAME,
                PASSWORD,
                ORG_ID
                )

            # Continue if the required information has been received
            if csrf_token and user_token and user_id:

                log.debug("Performing Command action.")
                command_action(csrf_token, user_token, user_id, ORG_ID)
                log.debug("Action complete.")

            # Handles when the required credentials were not received
            else:
                log.critical(
                    "No credentials or incorrect credentials "
                    "were provided."
                )

            # Calculate the time take to run and post it to the log
            elapsed_time = time.time() - start_run_time
            log.info("-------")
            log.info("Total time to complete %.2f", elapsed_time)

        # Gracefully handle an interrupt
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Logging out & aborting...")

        finally:
            if csrf_token and user_token:
                log.debug("Logging out.")
                logout(session, csrf_token, user_token)
            session.close()
            log.debug("Session closed.\nExiting...")
