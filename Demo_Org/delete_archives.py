"""
Author: Ian Young
Purpose: Iterate through all archives that are visible to a user and delete
them. This is ONLY to be used to keep a given org clean. Extreme caution is
advised since the changes this script will make to the org cannot be undone
once made.
"""

# Import essential libraries
import threading
import time
from datetime import datetime, timedelta, timezone
from os import getenv

import pytz
import requests
from colorama import Fore, Style, init
from dotenv import load_dotenv
from tzlocal import get_localzone

from tools import (
    avl_tree,
    custom_exceptions,
    log,
    login_and_get_tokens,
    logout,
    SharedParams,
)
from tools.api_endpoints import GET_ARCHIVE, DELETE_ARCHIVE

init(autoreset=True)  # Initialize colorized output

load_dotenv()  # Load credentials file

# Set final, global credential variables
USERNAME = getenv("")
PASSWORD = getenv("")
ORG_ID = getenv("")

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
d7a77639-e451-4d35-b18f-8fd8ae2cd0a6",
]

log.info("Building search tree.")
AVL_TREE = avl_tree.build_avl_tree(PERSISTENT_ARCHIVES)
log.info("%sSearch tree built.%s", Fore.GREEN, Style.RESET_ALL)

AGE_LIMIT = 14  # Delete anything older than 14 days


def read_verkada_camera_archives(params: SharedParams):
    """
    Iterates through all Verkada archives that are visible to a given user.

    :param params: Class that stores commonly used variables
    :type params: SharedParams
    :return: An array of archived video export IDs.
    :rtype: list
    """
    body = {
        "fetchOrganizationArchives": True,
        "fetchUserArchives": True,
        "pageSize": 1000000,
        "organizationId": params.org_id,
    }

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting archives.")
        response = params.session.post(GET_ARCHIVE, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Archive IDs retrieved. Returning values.")

        return response.json().get("videoExports", [])

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Read archives"
        ) from e


def get_archive_name(archive):
    """
    Extracts the name of the archive based on its label, tags, or videoExportId.

    :param archive: A dictionary representing an archive.
    :type archive: dict
    :return: The name of the archive.
    :rtype: str
    """
    if archive.get("label"):
        return archive.get("label")

    if archive.get("tags"):
        return archive.get("tags")

    return archive.get("videoExportId")


def localize_timestamp(epoch_timestamp, local_timezone):
    """
    Converts the epoch timestamp to the local timezone.

    :param epoch_timestamp: The epoch timestamp of the archive.
    :type epoch_timestamp: int
    :param local_timezone: The local timezone to convert to.
    :type local_timezone: datetime.tzinfo
    :return: The localized datetime object.
    :rtype: datetime
    """
    date_utc = datetime.fromtimestamp(epoch_timestamp, timezone.utc)
    date_utc = pytz.utc.localize(date_utc)
    return date_utc.astimezone(local_timezone)


def check_age(archive_time, age_limit):
    """
    Determines if an archive is older than the given age limit.

    :param archive_time: The time of the archive.
    :type archive_time: datetime
    :param age_limit: The age limit in days.
    :type age_limit: int
    :return: True if the archive should be deleted, False otherwise.
    :rtype: bool
    """
    current_time = datetime.now()
    time_difference = current_time - archive_time
    return time_difference > timedelta(days=age_limit)


def create_deletion_thread(
    video_export_id, params: SharedParams, archive_name
):
    """
    Creates a thread to delete an archive.

    :param video_export_id: The ID of the video export.
    :type video_export_id: str
    :param x_verkada_token: The Verkada token.
    :type x_verkada_token: str
    :param x_verkada_auth: The Verkada authentication.
    :type x_verkada_auth: str
    :param usr: The user initiating the deletion.
    :type usr: str
    :param archive_name: The name of the archive.
    :type archive_name: str
    :return: The thread created to delete the archive.
    :rtype: threading.Thread
    """
    return threading.Thread(
        target=remove_verkada_camera_archive,
        args=(
            video_export_id,
            params.x_verkada_token,
            params.x_verkada_auth,
            params.usr,
            archive_name,
        ),
    )


def process_archive(archive, params: SharedParams, age_limit):
    """
    Processes an individual archive, checking its timestamp and creating a
    deletion thread if necessary.

    :param archive: A dictionary representing an archive.
    :type archive: dict
    :param x_verkada_token: The Verkada token.
    :type x_verkada_token: str
    :param x_verkada_auth: The Verkada authentication.
    :type x_verkada_auth: str
    :param usr: The user initiating the deletion.
    :type usr: str
    :param age_limit: The age limit in days.
    :type age_limit: int
    :return: A list of threads created for deletion.
    :rtype: list
    """
    threads = []
    archive_name = get_archive_name(archive)
    if epoch_timestamp := archive.get("timeExported"):
        date_local = localize_timestamp(epoch_timestamp, get_localzone())
        archive_time = date_local.replace(tzinfo=None)

        if check_age(archive_time, age_limit):
            video_export_id = archive.get("videoExportId")
            result_node = avl_tree.search_in_avl_tree(
                AVL_TREE, video_export_id
            )

            if result_node is None:
                thread = create_deletion_thread(
                    video_export_id,
                    params,
                    archive_name,
                )
                threads.append(thread)
    return threads


def remove_verkada_camera_archives(
    params: SharedParams, archive_library, age_limit=AGE_LIMIT
):
    """
    Will iterate through all Verkada archives visible to a given user and
    delete them permanently.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkada organization.
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
            Style.RESET_ALL,
        )
        return
    log.debug("%sTest complete. Continuing...%s", Fore.GREEN, Style.RESET_ALL)

    if age_limit == 0:
        # Iterate through all video export IDs and remove them
        log.debug("Iterating through archive values.")
        for archive in archive_library:
            video_export_id = archive.get("videoExportId")

            log.debug("Searching AVL tree.")
            result_node = avl_tree.search_in_avl_tree(
                AVL_TREE, video_export_id
            )

            # Check if the archive has been marked "persistent"
            if result_node is None:
                log.debug(
                    "Age limit set to zero. Skipping age check."
                    "\nRunning for %s%s%s.",
                    Fore.MAGENTA,
                    video_export_id,
                    Style.RESET_ALL,
                )

                thread = threading.Thread(
                    target=remove_verkada_camera_archive,
                    args=(
                        video_export_id,
                        params,
                    ),
                )
                # Add the thread to the array
                threads.append(thread)

    else:
        threads.extend(
            process_archive(
                archive_library,
                params,
                age_limit,
            )
        )

    if threads:
        try:
            # Start in separate thread to speed up runtime
            for thread in threads:
                log.debug(
                    "Starting %s%s%s.",
                    Fore.LIGHTYELLOW_EX,
                    thread.name,
                    Style.RESET_ALL,
                )
                thread.start()

            # Join all threads back to the main parent thread
            for thread in threads:
                log.debug(
                    "Joining thread %s%s%s back to main.",
                    Fore.LIGHTYELLOW_EX,
                    thread.name,
                    Style.RESET_ALL,
                )
                thread.join()

        except threading.ThreadError as te:
            log.error(
                "%sA thread error occurred. %s%s",
                Fore.RED,
                te,
                Style.RESET_ALL,
            )
        except RuntimeWarning as rte:
            log.error(
                "%sAn error occurred during the runtime. %s%s",
                Fore.RED,
                rte,
                Style.RESET_ALL,
            )


def remove_verkada_camera_archive(params: SharedParams, video_export_id, name):
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
    :param usr: The user ID for a valid user in the Verkada organization.
    :type usr: str
    """
    body = {"videoExportId": video_export_id}

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    removed_archive = []

    log.debug("Searching AVL tree.")
    result_node = avl_tree.search_in_avl_tree(AVL_TREE, video_export_id)

    if result_node is None:
        try:
            # Post the delete request to the server
            log.debug(
                "Requesting deletion for %s%s%s.",
                Fore.MAGENTA,
                name,
                Style.RESET_ALL,
            )
            response = params.session.post(
                DELETE_ARCHIVE, json=body, headers=headers
            )
            response.raise_for_status()  # Raise an exception for HTTP errors
            log.info(
                "%sDeletion for %s%s%s processed.%s",
                Fore.GREEN,
                Fore.MAGENTA,
                name,
                Fore.GREEN,
                Style.RESET_ALL,
            )
            if removed_archive := response.json().get("videoExports", []):
                for archive in removed_archive:
                    log.info("Removed Archive: %s", name)
                    log.debug("%s", archive)
                    log.debug("-------")
            else:
                log.warning(
                    "Failed to remove Archive with videoExportId: %s", name
                )

        except requests.exceptions.RequestException as e:
            raise custom_exceptions.APIExceptionHandler(
                e, response, "Remove archives"
            ) from e
    else:
        log.debug(
            "Skipping %s%s%s.%sThis archive is marked as persistent.%s.",
            Fore.MAGENTA,
            name,
            Style.RESET_ALL,
            Fore.CYAN,
            Style.RESET_ALL,
        )

    return removed_archive


# Check if the script is being imported or ran directly
if __name__ == "__main__":
    with requests.Session() as archive_session:
        start_time = time.time()  # Start timing the script
        try:
            # Initialize the user session.
            if USERNAME and PASSWORD and ORG_ID:
                csrf_token, user_token, user_id = login_and_get_tokens(
                    archive_session, USERNAME, PASSWORD, ORG_ID
                )

                # Continue if the required information has been received
                if csrf_token and user_token and user_id:
                    runtime_params = SharedParams(
                        archive_session,
                        csrf_token,
                        user_token,
                        user_id,
                        ORG_ID,
                    )
                    log.debug("Retrieving archive library.")
                    archives = read_verkada_camera_archives(runtime_params)
                    log.debug(
                        "%sArchive library retrieved.%s",
                        Fore.GREEN,
                        Style.RESET_ALL,
                    )

                    log.debug("Entering remove archives method.")
                    remove_verkada_camera_archives(runtime_params, archives)
                    log.debug(
                        "%sProgram completed successfully.%s",
                        Fore.GREEN,
                        Style.RESET_ALL,
                    )

            # Handles when the required credentials were not received
            else:
                log.critical(
                    "%sNo credentials were provided during "
                    "the authentication process.%s",
                    Fore.RED,
                    Style.RESET_ALL,
                )

            # Calculate the time take to run and post it to the log
            elapsed_time = time.time() - start_time
            log.info("Total time to complete %.2f", elapsed_time)

        # Gracefully handle an interrupt
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Aborting...")

        finally:
            if ORG_ID and "csrf_token" in locals():
                logout(archive_session, csrf_token, user_token, ORG_ID)
            archive_session.close()
            log.debug("Session closed. Exiting...")
