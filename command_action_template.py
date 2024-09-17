"""
Author: Ian Young
Purpose: Serve as a template for logging in a user, performing an action,
and logging out.
"""

# Import essential libraries
import time
from os import getenv

import requests
from dotenv import load_dotenv

from tools import APIExceptionHandler, log, login_and_get_tokens, logout

load_dotenv()  # Load credentials file

# Set final, global credential variables
USERNAME = getenv("username")
PASSWORD = getenv("password")
ORG_ID = getenv("org_id")

# Set final, global URLs
ACTION_URL = ""  # Put the endpoint here


##############################################################################
################################  Requests  ##################################
##############################################################################


def command_action(
    action_session, x_verkada_token, x_verkada_auth, usr, org_id=ORG_ID
):
    """
    Perform an action in Command.

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
    # NOTE: Not all endpoints require a body.
    body = {"organizationId": org_id}

    # IMPORTANT: All endpoints will need this if not using apidocs.verkada.com
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr,
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
        raise APIExceptionHandler(e, response, "Log in") from e


##############################################################################
##################################  Main  ####################################
##############################################################################


# Check if the script is being imported or ran directly
if __name__ == "__main__":

    with requests.Session() as session:
        start_run_time = time.time()  # Start timing the script
        if USERNAME and PASSWORD and ORG_ID:
            csrf_token, user_token, user_id = None, None, None
            try:
                # Initialize the user session.
                csrf_token, user_token, user_id = login_and_get_tokens(
                    session, USERNAME, PASSWORD, ORG_ID
                )

                # Continue if the required information has been received
                if csrf_token and user_token and user_id:

                    log.debug("Performing Command action.")
                    command_action(csrf_token, user_token, user_id, ORG_ID)
                    log.debug("Action complete.")

                # Handles when the required credentials were not received
                else:
                    log.critical(
                        "No credentials or incorrect credentials were provided."
                    )

                # Calculate the time take to run and post it to the log
                elapsed_time = time.time() - start_run_time
                log.info("-------")
                log.info("Total time to complete %.2f", elapsed_time)

            # Gracefully handle an interrupt
            except KeyboardInterrupt:
                print(
                    "\nKeyboard interrupt detected. Logging out & aborting..."
                )

            finally:
                if csrf_token and user_token:
                    log.debug("Logging out.")
                    logout(session, csrf_token, user_token, ORG_ID)
                session.close()
                log.debug("Session closed.\nExiting...")
