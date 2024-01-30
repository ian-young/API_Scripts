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
import creds  # File with credentials

# Set final, global credential variables
USERNAME = creds.mc_u
PASSWORD = creds.get_password()
ORG_ID = creds.mc_oid

# Set final, global URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
ARCHIVE_URL = "https://vsubmit.command.verkada.com/library/export/list"
DELETE_URL = "https://vsubmit.command.verkada.com/library/export/delete"

# Set up the logger
log = logging.getLogger()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Mark what archives are to be "persistant"


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
    try:
        start_time = time.time()

        # Start the user session
        with requests.Session() as session:
            csrf_token, user_token, user_id = login_and_get_tokens()

            if csrf_token and user_token and user_id:
                log.debug("Entering remove archives method.")
                remove_verkada_camera_archives(csrf_token, user_token, user_id)
                log.debug("Program completed successfully.")

            else:
                log.critical("No credentials were provided during the authentication \
process.")

        elapsed_time = time.time() - start_time
        log.info(f"Total time to complete {elapsed_time:.2f}")
    except KeyboardInterrupt:
        print(f"\nKeyboard interrupt detected. Aborting...")

log.debug("Session closed. Exiting...")
