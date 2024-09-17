"""
Author: Ian Young
Purpose: Iterate through all archives that are visible to a user and delete
them. This is ONLY to be used to keep a given org clean. Extreme caution is
advised since the changes this script will make to the org cannot be undone
once made.
"""

# Import essential libraries
import time
from os import getenv

import requests
from dotenv import load_dotenv

from tools import APIExceptionHandler, log, login_and_get_tokens, logout
from tools.api_endpoints import GET_ARCHIVE

load_dotenv()  # Load credentials file

# Set final, global credential variables
USERNAME = getenv("")
PASSWORD = getenv("")
ORG_ID = getenv("")


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
            GET_ARCHIVE, json=body, headers=headers
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Archive IDs retrieved. Returning values.")

        return response.json().get("videoExports", [])

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        text = "Reading archives"
        raise APIExceptionHandler(e, response, text) from e


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
            if ORG_ID:
                csrf_token, user_token, user_id = None, None, None
                if USERNAME and PASSWORD:
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

                    logout(session, csrf_token, user_token, ORG_ID)

                else:
                    log.critical(
                        "No credentials were provided during the \
    authentication process."
                    )
            else:
                log.critical("Missing org id.")

        elapsed_time = time.time() - start_time
        log.info("Total time to complete %.2f", elapsed_time)
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Aborting...")

log.debug("Session closed. Exiting...")
