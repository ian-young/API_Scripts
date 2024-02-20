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
USERNAME = creds.lab_username
PASSWORD = creds.lab_password
ORG_ID = creds.lab_id

# Set final, global URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
ARCHIVE_URL = "https://vsubmit.command.verkada.com/library/export/list"
DELETE_URL = "https://vsubmit.command.verkada.com/library/export/delete"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"

# Set up the logger
log = logging.getLogger()
log.setLevel(logging.DEBUG)
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Mark what archives are to be "persistent"
PERSISTENT_ARCHIVES = [
    "c94be2a0-ca3f-4f3a-b208-8db8945bf40b|1706411022|1706411033|d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "c94be2a0-ca3f-4f3a-b208-8db8945bf40b|1702781302|1702781309|d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "c94be2a0-ca3f-4f3a-b208-8db8945bf40b|1694822217|1694822237|d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "c94be2a0-ca3f-4f3a-b208-8db8945bf40b|1694291875|1694291886|d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "c94be2a0-ca3f-4f3a-b208-8db8945bf40b|1693881720|1693881728|d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "4e6abc02-5242-47e7-b862-0b7b33db1de0|1689959460|1689959520|d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "01664a7f-b1f3-42bd-b1c2-069d85e9a0bf|1683758763|1683758809|d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
    "01664a7f-b1f3-42bd-b1c2-069d85e9a0bf|1683596280|1683596310|d7a77639-e451-4d35-b18f-8fd8ae2cd0a6"
]


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
        log.error(f"{Fore.RED}Connection timed out.{Style.RESET_ALL}")
        return None, None, None

    except requests.exceptions.TooManyRedirects:
        log.error(
            f"{Fore.RED}Too many redirects. "
            f"Aborting...{Style.RESET_ALL}"
        )
        return None, None, None

    except requests.exceptions.HTTPError:
        log.error(
            f"{Fore.RED}Returned with a non-200 code: {Style.RESET_ALL}"
            f"{response.status_code}"
        )
        return None, None, None

    except requests.exceptions.ConnectionError:
        log.error(
            f"{Fore.RED}Error connecting to the server."
            f"{Style.RESET_ALL}"
        )
        return None, None, None

    except requests.exceptions.RequestException as e:
        log.error(f"{Fore.RED}Verkada API Error: {e}{Style.RESET_ALL}")
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
        # Request the JSON archive library
        # Request the JSON archive library
        log.debug("Requesting archives.")
        response = session.post(ARCHIVE_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Archive IDs retrieved. Returning values.")

        return response.json().get("videoExports", [])

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"{Fore.RED}Connection timed out.{Style.RESET_ALL}")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"{Fore.RED}Too many redirects.\n"
                  f"Aborting...{Style.RESET_ALL}")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"{Fore.RED}Returned with a non-200 code: "
            f"{Style.RESET_ALL}{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(
            f"{Fore.RED}Error connecting to the server."
            f"{Style.RESET_ALL}"
        )
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"{Fore.RED}Verkada API Error: {e}{Style.RESET_ALL}")
        return None


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

    log.debug(f"Getting local timezone.")
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
            log.debug(f"Retrieved archive epoch timestamp: {epoch_timestamp}")

            if epoch_timestamp:
                # Take the epoch time and convert it to the local timezone
                date_utc = datetime.utcfromtimestamp(epoch_timestamp)
                date_utc = pytz.utc.localize(date_utc)
                date_local = date_utc.astimezone(local_timezone)

                # Localize timestamp from Epoch to local timezone
                log.debug(f"Localized archive time to {local_timezone}")
                date = date_local.strftime("%b %d, %Y %H:%M")  # Make string
                log.debug(f"Exported time: {date}")

                # Change String object to datetime object to run comparisons
                archive_time = datetime.strptime(date, "%b %d, %Y %H:%M")
                log.debug("Converted to datetime object. Comparing times.")

                # Get the time difference
                current_time = datetime.now()
                time_difference = current_time - archive_time
                log.debug(f"Time difference: {time_difference}")

                # If the clip is older than the age limit, run in thread
                if time_difference > timedelta(days=age_limit):
                    video_export_id = archive.get("videoExportId")
                    log.debug(
                        f"{Fore.MAGENTA}{archive_name}"
                        f"{Style.RESET_ALL} is older than {age_limit} days."
                    )
                    log.debug(
                        f"Checking if "
                        f"{Fore.MAGENTA}{archive_name}"
                        f"{Style.RESET_ALL} is persistent."
                    )

                    log.debug("Searching AVL tree")
                    result_node = avlTree.search_in_avl_tree(AVL_TREE,
                                                             video_export_id)

                    if result_node is None:
                        log.debug(
                            f"Creating thread for {Fore.MAGENTA}"
                            f"{archive_name}{Style.RESET_ALL}."
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
                            f"{Fore.MAGENTA}{archive_name}{Fore.CYAN} "
                            f"marked as persistent... Skipping."
                            f"{Style.RESET_ALL}"
                        )
                        # Aesthetic dividing line
                        log.debug("----------------------")
                else:
                    if result_node is None:
                        log.debug("Archive not marked as persistent.")
                        video_export_id = archive.get("videoExportId")
                        log.debug(
                            f"Creating thread for {Fore.MAGENTA}"
                            f"{archive_name}{Style.RESET_ALL}."
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

    log.debug(f"{Fore.LIGHTBLACK_EX}Thread array: {threads}{Style.RESET_ALL}")

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
    threads = []

    # Retrieve Verkada camera archives
    log.debug("Retrieving archives.")
    archives = read_verkada_camera_archives(
        x_verkada_token,
        x_verkada_auth,
        usr,
        org_id
    )
    log.debug("Archives received.")

    try:
        # Check if archives is iterable
        log.debug("Testing if archive variable is iterable.")
        iter(archives)
    except (TypeError, AttributeError):
        log.error(
            f"{Fore.RED}Error: Archives is not iterable or is None."
            f"{Style.RESET_ALL}"
        )
        return
    log.debug("Test complete. Continuing.")

    # Iterate through all video export IDs and remove them
    log.debug("Iterating through archive values")
    for archive in archives:
        video_export_id = archive.get("videoExportId")

        # Check if the archive has been marked "persistent"
        if (video_export_id not in PERSISTENT_ARCHIVES):
            log.debug(f"\nRunning for {video_export_id}")
            thread = threading.Thread(
                target=remove_verkada_camera_archive,
                args=(
                    video_export_id,
                    x_verkada_token,
                    x_verkada_auth,
                    usr
                ))

            # Start in seperate thread to speed up runtime
            log.debug(f"Starting thread {thread.name}.")
            threads.append(thread)
            thread.start()

    # Join all threads back to the main parent thread
    for thread in threads:
        log.debug(f"Joining thread {thread.name} back to main.")
        thread.join()

        except threading.ThreadError as te:
            log.error(
                f"{Fore.RED}A thread error occured. {te}{Style.RESET_ALL}")
        except RuntimeWarning as re:
            log.error(
                f"{Fore.RED}An error occured during the runtime. {re}"
                f"{Style.RESET_ALL}"
            )
        except Exception as e:
            log.error(
                f"{Fore.RED}An unexpected error occured. {e}"
                f"{Style.RESET_ALL}"
            )


def remove_verkada_camera_archive(video_export_id, x_verkada_token,
                                  x_verkada_auth, usr, name):
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
        # Post the delete request to the server
        log.debug("Requesting deletion.")
        response = session.post(DELETE_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Deletion processed. Returning JSON values.")

        # JSON response of updated value for the archive
        removed_archive = response.json().get("videoExports", [])

        # Communicate with the user which archive has been deleted
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
            log.error(f"{Fore.RED}Connection timed out.{Style.RESET_ALL}")

        except requests.exceptions.TooManyRedirects:
            log.error(
                f"{Fore.RED}Too many redirects. Aborting...{Style.RESET_ALL}")

        except requests.exceptions.HTTPError:
            log.error(f"Returned with a non-200 code: {response.status_code}")

        except requests.exceptions.ConnectionError:
            log.error(
                f"{Fore.RED}Error connecting to the server.{Style.RESET_ALL}")

        except requests.exceptions.RequestException as e:
            log.error(f"{Fore.RED}Verkada API Error: {e}{Style.RESET_ALL}")
    else:
        log.debug(
            f"Skipping {Fore.MAGENTA}{name}{Style.RESET_ALL}. "
            f"{Fore.CYAN}This archive is marked as persistent."
            f"{Style.RESET_ALL}"
        )


# Check if the script is being imported or ran directly
if __name__ == "__main__":
    try:
        start_time = time.time()  # Start timing the script

        # Initialize the user session.
        with requests.Session() as session:
            csrf_token, user_token, user_id = login_and_get_tokens()

            # Continue if the required information has been received
            # Continue if the required information has been received
            if csrf_token and user_token and user_id:
                log.debug("Retrieving archive library.")
                archives = read_verkada_camera_archives(
                    csrf_token, user_token, user_id, ORG_ID)
                log.debug(
                    f"{Fore.GREEN}Archive library retrieved."
                    f"{Style.RESET_ALL}"
                )

                log.debug("Entering remove archives method.")
                remove_verkada_camera_archives(csrf_token, user_token, user_id)
                log.debug("Program completed successfully.")

            # Handles when the required credentials were not received
            else:
                log.critical("No credentials were provided during the \
authentication process.")

        # Calculate the time take to run and post it to the log
        elapsed_time = time.time() - start_time
        log.info(f"Total time to complete {elapsed_time:.2f}")

    # Gracefully handle an interrupt
    except KeyboardInterrupt:
        print(f"\nKeyboard interrupt detected. Aborting...")

        finally:
            session.close()
            log.debug("Session closed. Exiting...")
