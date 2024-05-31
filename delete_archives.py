"""
Author: Ian Young
Purpose: Iterate through all archives that are visible to a user and delete
them. This is ONLY to be used to keep a given org clean. Extreme caution is
advised since the changes this script will make to the org cannot be undone
once made.
"""
# Import essential libraries
<<<<<<< HEAD
from re import search
import requests
import logging
import threading
import time
import creds  # File with credentials
import pytz
import colorama
from datetime import datetime, timedelta
from tzlocal import get_localzone
=======
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from os import getenv

import colorama
import pytz
import requests
>>>>>>> 522024f (Linted)
from colorama import Fore, Style
from dotenv import load_dotenv
from tzlocal import get_localzone

import avl_tree  # File to work with trees
import custom_exceptions  # Import custom exceptions to save space

colorama.init(autoreset=True)  # Initialize colorized output

# Set final, global credential variables
<<<<<<< HEAD
USERNAME = creds.lab_username
PASSWORD = creds.lab_password
ORG_ID = creds.lab_id
=======
USERNAME = getenv("")
PASSWORD = getenv("")
ORG_ID = getenv("")
>>>>>>> 522024f (Linted)

# Set final, global URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
ARCHIVE_URL = "https://vsubmit.command.verkada.com/library/export/list"
DELETE_URL = "https://vsubmit.command.verkada.com/library/export/delete"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"

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
AVL_TREE = avl_tree.build_avl_tree(PERSISTENT_ARCHIVES)
log.info(
    "%sSearch tree built.%s",
    Fore.GREEN,
    Style.RESET_ALL
)

AGE_LIMIT = 14  # Delete anything older than 14 days


def login_and_get_tokens(login_session, username=USERNAME, password=PASSWORD, org_id=ORG_ID):
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
        log.debug("Requesting session.")
        response = login_session.post(LOGIN_URL, json=login_data)
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


def read_verkada_camera_archives(archive_session, x_verkada_token,
                                 x_verkada_auth, usr, org_id=ORG_ID):
    """
    Iterates through all Verkada archives that are visible to a given user.

    :param archive_session: The session to use when authenticating.
    :type archive_session: requests.Session
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
        # Request the JSON archive library
        log.debug("Requesting archives.")
        response = archive_session.post(
            ARCHIVE_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Archive IDs retrieved. Returning values.")

        return response.json().get("videoExports", [])

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Read archives")


def check_archive_timestamp(archive_library, x_verkada_token, x_verkada_auth,
                            usr, age_limit=AGE_LIMIT):
    """
    Will iterate through the archive library and call a delete for any clip
    that is older than the given time limit. If the time limit is set to '0'
    then this function is skipped completely.

    :param archive_library: The JSON formatted list of all visible archives in
    a Verkada organization.
    :type archive_library: list
    :param age_limit: The age limit set in days for the oldest archive to be
    kept if it is not found in the persistent list.
    :type age_limit: int
    :return: A list of threads with individual archives to delete from 
    Verkada Command.
    :rtype: list
    """
    threads = []  # An array to be filled with threads with archives to delete
    video_export_id, archive_name, result_node = '', '', None  # Initialize

    log.debug("Getting local timezone.")
    local_timezone = get_localzone()  # Load the local timezone for the device
    log.debug("Timezone received.")

    if archive_library:
        log.debug("----------------------")  # Aesthetic dividing line
        for archive in archive_library:
            # Get the name of the archive
            if archive.get('label') != '':
                archive_name = archive.get('label')

            elif archive.get('tags') != []:
                archive_name = archive.get('tags')

            else:
                archive_name = archive.get('videoExportId')

            # Get the time of the archived clip
            epoch_timestamp = archive.get("timeExported")
            log.debug(
                "Retrieved archive epoch timestamp: %d",
                epoch_timestamp
            )

            if epoch_timestamp:
                # Take the epoch time and convert it to the local timezone
                date_utc = datetime.fromtimestamp(epoch_timestamp,
                                                  timezone.utc)
                date_utc = pytz.utc.localize(date_utc)
                date_local = date_utc.astimezone(local_timezone)

                # Localize timestamp from Epoch to local timezone
                log.debug("Localized archive time to %s", str(local_timezone))
                date = date_local.strftime("%b %d, %Y %H:%M")  # Make string
                log.debug("Exported time: %s", str(date))

                # Change String object to datetime object to run comparisons
                archive_time = datetime.strptime(date, "%b %d, %Y %H:%M")
                log.debug("Converted to datetime object. Comparing times.")

                # Get the time difference
                current_time = datetime.now()
                time_difference = current_time - archive_time
                log.debug("Time difference: %s", str(time_difference))

                # If the clip is older than the age limit, run in thread
                if time_difference > timedelta(days=age_limit):
                    video_export_id = archive.get("videoExportId")
                    log.debug(
                        "%s%s%s is older than %d days.",
                        Fore.MAGENTA,
                        archive_name,
                        Style.RESET_ALL,
                        age_limit
                    )
                    log.debug(
                        "Checking if %s%s%s is persistent.",
                        Fore.MAGENTA,
                        archive_name,
                        Style.RESET_ALL
                    )

                    log.debug("Searching AVL tree")
                    result_node = avl_tree.search_in_avl_tree(AVL_TREE,
                                                              video_export_id)

                    if result_node is None:
                        log.debug(
                            "Creating thread for %s%s%s.",
                            Fore.MAGENTA,
                            archive_name,
                            Style.RESET_ALL
                        )
                        thread = threading.Thread(
                            target=remove_verkada_camera_archive,
                            args=(video_export_id, x_verkada_token,
                                  x_verkada_auth, usr, archive_name)
                        )
                        log.debug("Thread appended to list.")
                        threads.append(thread)
                        # Aesthetic dividing line
                        log.debug("----------------------")
                    else:
                        log.info(
                            "%s%s%s marked as persistent... Skipping.%s",
                            Fore.MAGENTA,
                            archive_name,
                            Fore.CYAN,
                            Style.RESET_ALL
                        )
                        # Aesthetic dividing line
                        log.debug("----------------------")
                else:
                    if result_node is None:
                        log.debug("Archive not marked as persistent.")
                        video_export_id = archive.get("videoExportId")
                        log.debug(
                            "Creating thread for %s%s%s.",
                            Fore.MAGENTA,
                            archive_name,
                            Style.RESET_ALL
                        )

                        thread = threading.Thread(
                            target=remove_verkada_camera_archive,
                            args=(video_export_id, x_verkada_token,
                                  x_verkada_auth, usr, archive_name)
                        )
                        log.debug("Thread appended to list.")
                        threads.append(thread)
                        # Aesthetic dividing line
                        log.debug("----------------------")

    log.debug(
        "%sThread array: %s%s.", Fore.LIGHTBLACK_EX, threads, Style.RESET_ALL)

    return threads


def remove_verkada_camera_archives(x_verkada_token, x_verkada_auth,
                                   usr, archive_library, age_limit=AGE_LIMIT):
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
    :param archive_library: The JSON formatted list of all visible archives in
    a Verkada organization.
    :type archive_library: list
    :param age_limit: The age limit set in days for the oldest archive to be
    kept if it is not found in the persistent list.
    :type age_limit: int
    :return: None
    :rtype: None
    """
    threads = []  # Array to be filled with archives to delete

    log.debug("Archive library: ")
    for archive in archive_library:
        log.debug("%s%s%s", Fore.LIGHTBLACK_EX, archive, Style.RESET_ALL)
        log.debug("------------")

    try:
        # Check if archives is iterable
        log.debug("Testing if archive library variable is iterable.")
        iter(archive_library)
    except (TypeError, AttributeError):
        log.error(
            "%sError: Archives is not iterable or is None.%s",
            Fore.RED,
            Style.RESET_ALL
        )
        return
    log.debug("%sTest complete. Continuing...%s", Fore.GREEN, Style.RESET_ALL)

    if age_limit == 0:
        # Iterate through all video export IDs and remove them
        log.debug("Iterating through archive values.")
        for archive in archive_library:
            video_export_id = archive.get("videoExportId")

            log.debug("Searching AVL tree.")
            result_node = avl_tree.search_in_avl_tree(AVL_TREE,
                                                      video_export_id)

            # Check if the archive has been marked "persistent"
            if result_node is None:
                log.debug(
                    "Age limit set to zero. Skipping age check."
                    "\nRunning for %s%s%s.",
                    Fore.MAGENTA,
                    video_export_id,
                    Style.RESET_ALL
                )

                thread = threading.Thread(
                    target=remove_verkada_camera_archive,
                    args=(
                        video_export_id,
                        x_verkada_token,
                        x_verkada_auth,
                        usr
                    ))
                # Add the thread to the array
                threads.append(thread)

    else:
        threads.extend(check_archive_timestamp(
            archive_library,
            x_verkada_token,
            x_verkada_auth,
            usr,
            age_limit
        ))

    if threads:
        try:
            # Start in seperate thread to speed up runtime
            for thread in threads:
                log.debug(
                    "Starting %s%s%s.",
                    Fore.LIGHTYELLOW_EX,
                    thread.name,
                    Style.RESET_ALL
                )
                thread.start()

            # Join all threads back to the main parent thread
            for thread in threads:
                log.debug(
                    "Joining thread %s%s%s back to main.",
                    Fore.LIGHTYELLOW_EX,
                    thread.name,
                    Style.RESET_ALL
                )
                thread.join()

        except threading.ThreadError as te:
            log.error(
                "%sA thread error occured. %s%s",
                Fore.RED,
                te,
                Style.RESET_ALL
            )
        except RuntimeWarning as rte:
            log.error(
                "%sAn error occured during the runtime. %s%s",
                Fore.RED,
                rte,
                Style.RESET_ALL
            )


def remove_verkada_camera_archive(remove_session, video_export_id,
                                  x_verkada_token, x_verkada_auth, usr, name):
    """
    Removes a given Verkada archive that is visible to the given user and 
    deletes it permanently.

    :param remove_session: The authenticated session to use to remove archives.
    :type remove_session: requests.Session
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

    log.debug("Searching AVL tree.")
    result_node = avl_tree.search_in_avl_tree(AVL_TREE, video_export_id)

    if result_node is None:
        try:
            # Post the delete request to the server
            log.debug(
                "Requesting deletion for %s%s%s.",
                Fore.MAGENTA,
                name,
                Style.RESET_ALL
            )
            response = remove_session.post(
                DELETE_URL, json=body, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            log.info(
                "%sDeletion for %s%s%s processed.%s",
                Fore.GREEN,
                Fore.MAGENTA,
                name,
                Fore.GREEN,
                Style.RESET_ALL
            )
            # JSON response of updated value for the archive
            removed_archive = response.json().get("videoExports", [])

            # Communicate with the user which archive has been deleted
            if removed_archive:
                for archive in removed_archive:
                    log.info("Removed Archive: %s", name)
                    log.debug("%s", archive)
                    log.debug("-------")
            else:
                log.warning(
                    "Failed to remove Archive with videoExportId: %s",
                    name
                )

                return removed_archive

        # Handle exceptions
        except requests.exceptions.RequestException as e:
            raise custom_exceptions.APIExceptionHandler(
                e, response, "Remove archives")
    else:
        log.debug(
            "Skipping %s%s%s.%sThis archive is marked as persistent.%s.",
            Fore.MAGENTA,
            name,
            Style.RESET_ALL,
            Fore.CYAN,
            Style.RESET_ALL
        )


# Check if the script is being imported or ran directly
if __name__ == "__main__":
    with requests.Session() as session:
        start_time = time.time()  # Start timing the script
        try:
            # Initialize the user session.
            csrf_token, user_token, user_id = login_and_get_tokens(session)

            # Continue if the required information has been received
            if csrf_token and user_token and user_id:
                log.debug("Retrieving archive library.")
                archives = read_verkada_camera_archives(
                    session, csrf_token, user_token, user_id, ORG_ID)
                log.debug(
                    "%sArchive library retrieved.%s",
                    Fore.GREEN,
                    Style.RESET_ALL
                )

                log.debug("Entering remove archives method.")
                remove_verkada_camera_archives(
                    session, csrf_token, user_token, user_id, archives)
                log.debug(
                    "%sProgram completed successfully.%s",
                    Fore.GREEN,
                    Style.RESET_ALL
                )

            # Handles when the required credentials were not received
            else:
                log.critical(
                    "%sNo credentials were provided during "
                    "the authentication process.%s",
                    Fore.RED,
                    Style.RESET_ALL
                )

            # Calculate the time take to run and post it to the log
            elapsed_time = time.time() - start_time
            log.info("Total time to complete %.2f", elapsed_time)

<<<<<<< HEAD
    # Gracefully handle an interrupt
    except KeyboardInterrupt:
        print(f"\nKeyboard interrupt detected. Aborting...")
=======
        # Gracefully handle an interrupt
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Aboting...")
>>>>>>> 522024f (Linted)

        finally:
            session.close()
            log.debug("Session closed. Exiting...")
