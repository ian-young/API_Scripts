"""
Author: Ian Young
Purpose: Will take a person's email, first name and last name from a csv
and create a Command account for them with org admin privileges.
"""

import csv
import logging
from datetime import datetime
from os import getenv

import requests
from dotenv import load_dotenv

from QoL import login_and_get_tokens, logout
from QoL.api_endpoints import PROMOTE_ORG_ADMIN, CREATE_USER
from QoL.custom_exceptions import APIExceptionHandler

log = logging.getLogger()
LOG_LEVEL = logging.INFO
log.setLevel(LOG_LEVEL)
logging.basicConfig(
    level=LOG_LEVEL, format="%(asctime)s - %(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

load_dotenv()  # Import credentials file

ORG_ID = getenv("")
USERNAME = getenv("")
PASSWORD = getenv("")
TOTP = getenv("")  # Leave blank if you don't have one on the account
API_KEY = getenv("")
FILE_PATH = (
    "/Users/ian.young/Documents/.scripts/API_Scripts/VCE/"
    "VCE_AC_Specialist_Check_ins_GuestLog - 2024-07-17.csv"
)


def read_csv(file_name):
    """
    Reads a CSV file and extracts the first name, last name, and email columns.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        list of dict: A list of dictionaries containing 'first_name', 'last_name', and 'email'.
    """
    data = []

    # Open file
    with open(file_name, mode="r", newline="", encoding="UTF-8") as file:
        # Set reader
        csv_reader = csv.DictReader(file)

        log.debug("Parsing csv")
        # Extract useful columns
        for row in csv_reader:
            try:
                name_parts = row["Guest Name"].split()
                data.append(
                    {
                        "First Name": name_parts[0],
                        "Last Name": name_parts[-1],
                        "Guest Email": row["Guest Email"],
                    }
                )

            except IndexError:
                data.append(
                    {
                        "First Name": "",
                        "Last Name": "",
                        "Guest Email": row["Guest Email"],
                    }
                )
                log.error(
                    "%s: Either first name or last name was provided.",
                    str(row),
                )
                continue

    log.info("Data retrieved")
    return data


def grant_org_admin(
    x_verkada_token, usr_id, target_id, management_session, org_id=ORG_ID
):
    """
    Grant organization admin permissions to a user within a specified organization.

    Args:
        x_verkada_token (str): The Verkada token for authentication.
        usr_id (str): The user ID performing the action.
        target_id (str): The ID of the user to grant admin permissions to.
        org_id (str, optional): The ID of the organization. Defaults to ORG_ID.

    Returns:
        None

    Raises:
        APIExceptionHandler: If an error occurs during the API request.

    Examples:
        grant_org_admin(
            "xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyy",
            "zzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz"
        )
    """
    headers = {
        "x-verkada-token": x_verkada_token,
        "x-verkada-user_id": usr_id,
        "x-verkada-organization-id": org_id,
    }

    body = {
        "targetUserId": target_id,
        "organizationId": org_id,
        "returnPermissions": False,
        "grant": [
            {
                "entityId": org_id,
                "roleKey": "ORG_MANAGER",
                "permission": "ORG_MANAGER",
            }
        ],
        "revoke": [],
    }

    try:
        log.info("Attempting to promote to org admin.")
        response = management_session.post(
            PROMOTE_ORG_ADMIN, headers=headers, json=body, timeout=3
        )
        response.raise_for_status()
        log.info("Promoted to org admin.")

    except requests.exceptions.RequestException as e:
        raise APIExceptionHandler(e, response, "Promote org admin") from e


def create_vce_user(user_info_list, api_key=API_KEY):
    """
    Create VCE user using the provided user information list.

    Args:
        user_info_list (list): A list of dictionaries containing user
            information including "First Name", "Last Name", and "Email".
        api_key (str): The API key to authenticate the request. Defaults
            to API_KEY.

    Returns:
        list: A list of all emails of the newly created accounts.

    Raises:
        APIExceptionHandler: If an error occurs during the API request.
    """
    emails = []

    log.debug("User list:\n%s", user_info_list)

    with requests.Session() as session:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": api_key,
        }
        csrf_token, user_token, user_id = None, None, None

        try:
            # Initialize the user session.
            if USERNAME and PASSWORD and ORG_ID:
                csrf_token, user_token, user_id = login_and_get_tokens(
                    session, USERNAME, PASSWORD, ORG_ID, TOTP
                ):

                for result in user_info_list:
                    log.debug("Loading result info into JSON body.")
                    body = {
                        "first_name": result["First Name"],
                        "last_name": result["Last Name"],
                        "email": result["Guest Email"],
                    }
                    emails.append(result["Guest Email"])
                    log.debug(body)

                    log.debug("Posting request to create user.")
                    response = session.post(
                        CREATE_USER, headers=headers, json=body, timeout=3
                    )

                    if response.status_code != 500:
                        response.raise_for_status()

                    else:
                        log.warning("User already exists. Skipping.")
                        continue

                    data = response.json()
                    log.info(
                        "User %s %s has been successfully created. An email has been "
                        "sent to %s.",
                        result["First Name"],
                        result["Last Name"],
                        result["Guest Email"],
                    )

                    grant_org_admin(csrf_token, user_id, data["user_id"], session)

                return emails

            # Handles when the required credentials were not received
            else:
                log.critical(
                    "%sNo credentials were provided during "
                    "the authentication process or audit log "
                    "could not be retrieved.%s",
                    Fore.MAGENTA,
                    Style.RESET_ALL,
                )

        except requests.exceptions.RequestException as e:
            raise APIExceptionHandler(e, response, "Create user") from e

        finally:
            log.debug("Logging out.")
            if user_id and user_token:
                logout(session, csrf_token, user_id, ORG_ID)
            session.close()
            log.info("Session closed.\nExiting...")


participants = create_vce_user(read_csv(FILE_PATH))
print(f"Emails were sent at {datetime.now().date()}")

for person in participants:
    print(person, end=", ")
