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
from datetime import datetime
from os import getenv

import pytz
import requests
from dotenv import load_dotenv
from tzlocal import get_localzone

from QoL import login_and_get_tokens, logout, custom_exceptions

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
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)


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
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Read Archives"
        ) from e


def name_verkada_camera_archives(archive_library):
    """
    Lists and gives a name to every archive in an org

    :param archive_library: Library of all archives visible to the user.
    :type archive_library: list
    """
    local_timezone = get_localzone()

    log.info("----------------------")  # Aesthetic dividing line
    if archive_library:
        for archive in archive_library:
            if epoch_timestamp := archive.get("startBefore"):
                date_utc = datetime.utcfromtimestamp(epoch_timestamp)
                date_utc = pytz.utc.localize(date_utc)
                date_local = date_utc.astimezone(local_timezone)
                print(local_timezone)
                date = date_local.strftime("%b %d, %Y %H:%M")
                log.debug("Exported time: %s", date)

            else:
                log.warning("Missing timestamp from archive.")

            if archive.get("label") != "":
                log.info(
                    "%s\nArchive label: %s\n%s",
                    date,
                    archive.get("label"),
                    archive.get("videoExportId"),
                )
            elif archive.get("tags") != []:
                log.info(
                    "%s\nArchive has no name. Tags %s\n%s",
                    date,
                    archive.get("tags"),
                    archive.get("videoExportId"),
                )
            else:
                log.info(date)
                log.info(
                    "No name found. Archive ID: %s",
                    archive.get("videoExportId"),
                )
            log.info("----------------------")  # Aesthetic dividing line

    else:
        log.critical("Empty library.")


# Check if the script is being imported or ran directly
if __name__ == "__main__":
    try:
        start_time = time.time()

        # Start the user session
        with requests.Session() as session:
            if USERNAME and PASSWORD and ORG_ID:
                csrf_token, user_token, user_id = login_and_get_tokens(
                    session, USERNAME, PASSWORD, ORG_ID
                )

            if csrf_token and user_token and user_id:
                log.debug("Reading archives list.")
                name_verkada_camera_archives(
                    read_verkada_camera_archives(
                        session, csrf_token, user_token, user_id
                    )
                )
                log.debug("Reached EoL.")

            else:
                log.critical(
                    "No credentials were provided during the "
                    "authentication process."
                )

        elapsed_time = time.time() - start_time
        log.info("Total time to complete %.2fs.", elapsed_time)
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Aborting...")

    finally:
        if ORG_ID and csrf_token:
            logout(session, csrf_token, user_token, user_id)
        session.close()

log.debug("Session closed. Exiting...")
