# Author: Ian Young
# Purpose: Iterate through all archives that are visible to a user and delete
# them. This is ONLY to be used to keep a given org clean. Extreme caution is
# advised since the changes this script will make to the org cannot be undone
# once made.

# Import essential libraries
import requests
import logging
import threading
import time
import pytz
import colorama
import avlTree  # File to work with trees
from datetime import datetime, timedelta
from os import getenv
from tzlocal import get_localzone
from colorama import Fore, Style
from dotenv import load_dotenv

colorama.init(autoreset=True)  # Initialize colorized output

load_dotenv()

# Set final, global credential variables
USERNAME = getenv("lab_username")
PASSWORD = getenv("lab_password")
ORG_ID = getenv("lab_id")

# Set final, global URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
ARCHIVE_URL = "https://vsubmit.command.verkada.com/library/export/list"
DELETE_URL = "https://vsubmit.command.verkada.com/library/export/delete"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"

# Set up the logger
log = logging.getLogger()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Mark what archives are to be "persistent"
PERSISTENT_ARCHIVES = [
    "c94be2a0-ca3f-4f3a-b208-8db8945bf40b|1706411022|1706411033|\
d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "c94be2a0-ca3f-4f3a-b208-8db8945bf40b|1702781302|1702781309|\
d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "c94be2a0-ca3f-4f3a-b208-8db8945bf40b|1694822217|1694822237|\
d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "c94be2a0-ca3f-4f3a-b208-8db8945bf40b|1694291875|1694291886|\
d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "c94be2a0-ca3f-4f3a-b208-8db8945bf40b|1693881720|1693881728|\
d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "4e6abc02-5242-47e7-b862-0b7b33db1de0|1689959460|1689959520|\
d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "01664a7f-b1f3-42bd-b1c2-069d85e9a0bf|1683758763|1683758809|\
d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
       "01664a7f-b1f3-42bd-b1c2-069d85e9a0bf|1683596280|1683596310|\
d7a77639-e451-4d35-b18f-8fd8ae2cd0a6"
]

log.info("Building search tree.")
AVL_TREE = avlTree.build_avl_tree(PERSISTENT_ARCHIVES)
log.info(f"{Fore.GREEN}Search tree built.{Style.RESET_ALL}")

AGE_LIMIT = 14  # Delete anything older than 14 days


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
        log.error(f"Returned with a non-200 code: {response.status_code}")
        return None, None, None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None, None, None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None, None, None


def logout(x_verkada_token, x_verkada_auth, org_id=ORG_ID):
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

        log.info("Logging out:")

    except requests.exceptions.Timeout:
        log.error("The request has timed out.")

    except requests.exceptions.TooManyRedirects:
        log.error("Too many HTTP redirects.")

    except requests.HTTPError as e:
        log.error(f"An error has occured\n{e}")

    except requests.exceptions.ConnectionError:
        log.error("Error connecting to the server.")

    except requests.exceptions.RequestException:
        log.error("API error.")

    except KeyboardInterrupt:
        log.warning("Keyboard interrupt detected. Exiting...")

    finally:
        session.close()


def read_verkada_camera_archives(x_verkada_token, x_verkada_auth, usr,
                                 org_id=ORG_ID):
    """
    Iterates through all Verkada archives that are visible to a given user.

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
    body = {
        "fetchOrganizationArchives": True,
        "fetchUserArchives": True,
        "pageSize": 1000000,
        "organizationId": org_id
    }

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    try:
        log.debug("Requesting archives.")
        response = session.post(ARCHIVE_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Archive IDs retrieved. Returning values.")

        return response.json().get("videoExports", [])

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects. Aborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(f"Returned with a non-200 code: {response.status_code}")
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


def remove_verkada_camera_archives(x_verkada_token, x_verkada_auth,
                                   usr, org_id=ORG_ID):
    """
    Will iterate through all Verkada archives visible to a given user and
    delete them permanently.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: None
    :rtype: None
    """
    threads = []
    # Retrieve Verkada camera archives
    log.debug("Retrieving archives.")
    archives = read_verkada_camera_archives(x_verkada_token, x_verkada_auth,
                                            usr, org_id)
    log.debug("Archives received.")

    log.debug("Testing if archive variable is iterable.")
    try:
        # Check if archives is iterable
        iter(archives)
    except (TypeError, AttributeError):
        log.error("Error: Archives is not iterable or is None.")
        return
    log.debug("Test passed. Continuing.")

    # Iterate through all video export IDs and remove them
    log.debug("Iterating through archive values")
    for archive in archives:
        video_export_id = archive.get("videoExportId")

        log.debug(f"\nRunning for {video_export_id}")
        thread = threading.Thread(target=remove_verkada_camera_archive, args=(
            video_export_id, x_verkada_token, x_verkada_auth, usr))

        # Start in seperate thread to speed up runtime
        threads.append(thread)
        thread.start()

    # Join all threads back to the main parent thread
    for thread in threads:
        thread.join()


def remove_verkada_camera_archive(video_export_id, x_verkada_token,
                                  x_verkada_auth, usr):
    """
    Removes a given Verkada archive that is visible to the given user and 
    deletes it permanently.

    :param video_export_id: The id of the Verkada camera archive to delete.
    :type video_export_id: str
    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    """
    body = {
        "videoExportId": video_export_id
    }

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    try:
        log.debug("Requesting deletion.")
        response = session.post(DELETE_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Deletion processed. Returning JSON values.")

        removed_archive = response.json().get("videoExports", [])

        if removed_archive:
            for archive in removed_archive:
                if archive.get('label') != '':
                    log.info(f"Removed Archive: {archive.get('label')}")
                else:
                    log.info(f"Removed {archive.get('videoExportId')}")
            else:
                log.warning(f"Failed to remove Archive with videoExportId: \
                        {video_export_id}")

        return removed_archive

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects. Aborting...")

    except requests.exceptions.HTTPError:
        log.error(f"Returned with a non-200 code: {response.status_code}")

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")


# Check if the script is being imported or ran directly
if __name__ == "__main__":
    with requests.Session() as session:
        start_time = time.time()  # Start timing the script
        try:
            # Initialize the user session.
            csrf_token, user_token, user_id = login_and_get_tokens()

            if csrf_token and user_token and user_id:
                log.debug("Entering remove archives method.")
                remove_verkada_camera_archives(csrf_token, user_token, user_id)
                log.debug("Program completed successfully.")

            else:
                log.critical("No credentials were provided during the authentication \
process.")

            # Calculate the time take to run and post it to the log
            elapsed_time = time.time() - start_time
            log.info(f"Total time to complete {elapsed_time:.2f}")

        # Gracefully handle an interrupt
        except KeyboardInterrupt:
            print(f"\nKeyboard interrupt detected. Aboting...")

        finally:
            session.close()
            log.debug("Session closed. Exiting...")
