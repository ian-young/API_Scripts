# Author: Ian Young
# Purpose: Serve as a template for logging in a user, performing an action,
# and logging out.

# Import essential libraries
import requests
import logging
import time
from os import getenv
from dotenv import load_dotenv

load_dotenv()

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


def login_and_get_tokens(username=USERNAME, password=PASSWORD, org_id=ORG_ID):
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
        "org_id": org_id,
    }

    try:
        # Request the user session
        log.debug("Requesting session.")
        response = session.post(LOGIN_URL, json=login_data)
        response.raise_for_status()
        log.debug("Session opened.")

        # Extract relevant information from the JSON response
        log.debug("Parsing JSON response.")
        json_response = response.json()
        csrf_token = json_response.get("csrfToken")
        user_token = json_response.get("userToken")
        user_id = json_response.get("userId")
        log.debug("Response parsed. Returning values.")

        return csrf_token, user_token, user_id

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None, None, None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects. Aborting...")
        return None, None, None

    except requests.exceptions.HTTPError:
        log.error(
            f"Returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None, None, None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None, None, None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None, None, None


def logout(x_verkada_token, x_verkada_auth, org_id=ORG_ID):
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
        "x-verkada-orginization": org_id
    }

    body = {
        "logoutCurrentEmailOnly": True
    }

    try:
        response = session.post(LOGOUT_URL, headers=headers, json=body)
        response.raise_for_status()

        log.info("Logging out.")

    except requests.exceptions.Timeout:
        log.error("The request has timed out.")

    except requests.exceptions.TooManyRedirects:
        log.error("Too many HTTP redirects.")

    except requests.HTTPError as e:
        log.error(f"An error has occured: {e}")

    except requests.exceptions.ConnectionError:
        log.error("Error connecting to the server.")

    except requests.exceptions.RequestException:
        log.error("API error.")

    except KeyboardInterrupt:
        log.warning("Keyboard interrupt detected. Exiting...")

    finally:
        session.close()


##############################################################################
                            #   Requests   #
##############################################################################


def command_action(x_verkada_token, x_verkada_auth, usr,
            org_id=ORG_ID):
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
        response = session.post(ACTION_URL, json=body, headers=headers)
        response.raise_for_status()
        log.debug("-------")
        log.debug("Action completed.")

        return response.json()  # Return the endpoint response for computing.

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Cameras returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


##############################################################################
                                #   Main   #
##############################################################################


# Check if the script is being imported or ran directly
if __name__ == "__main__":

    with requests.Session() as session:
        start_run_time = time.time()  # Start timing the script
        try:
            # Initialize the user session.
            csrf_token, user_token, user_id = login_and_get_tokens()

            # Continue if the required information has been received
            if csrf_token and user_token and user_id:

                log.debug("Performing Command action.")
                command_action(csrf_token, user_token, user_id, ORG_ID)
                log.debug(f"Action complete.")

            # Handles when the required credentials were not received
            else:
                log.critical(
                    f"No credentials or incorrect credentials "
                    f"were provided."
                )

            # Calculate the time take to run and post it to the log
            elapsed_time = time.time() - start_run_time
            log.info("-------")
            log.info(f"Total time to complete {elapsed_time:.2f}")

        # Gracefully handle an interrupt
        except KeyboardInterrupt:
            print(f"\nKeyboard interrupt detected. Logging out & aborting...")

        finally:
            if csrf_token and user_token:
                log.debug("Logging out.")
                logout(csrf_token, user_token)
            session.close()
            log.debug("Session closed.\nExiting...")
