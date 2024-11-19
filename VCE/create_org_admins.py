"""
Authors: Ian Young, Elmar Aliyev
Purpose: Will take a person's email, first name and last name from a csv
and create a Command account for them with org admin privileges.
"""

import logging
import sys
from datetime import datetime
from os import getenv

import pandas as pd
import requests
from dotenv import load_dotenv

sys.path.append("/Users/ianyoung/Documents/.scripts/API_Scripts")
from QoL import login_and_get_tokens, logout
from QoL.get_key import get_api_token
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

API_KEY = getenv("denver_key")
USERNAME = getenv("denver_user")
PASSWORD = getenv("denver_pass")
ORG_ID = getenv("denver_id")
TOTP = getenv("denver_secret")
FILE_PATH = (
    "/Users/ianyoung/Documents/.scripts/API_Scripts/VCE/guest_csvs/"
    "VCE_AC_Specialist_Check_ins_GuestLog - 2024-11-19.csv"
)
TOKEN = get_api_token(API_KEY)


def read_csv(file_name):
    """
    Reads a CSV file and extracts the first name, last name, and email columns.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        list of dict: A list of dictionaries containing 'first_name', 'last_name', and 'email'.
    """
    try:
        return extract_data(file_name)
    except FileNotFoundError:
        log.error("The specified CSV file was not found: %s", file_name)
        return []
    except pd.errors.EmptyDataError:
        log.error("The CSV file is empty: %s", file_name)
        return []
    except pd.errors.ParserError:
        log.error("Error parsing the CSV file: %s", file_name)
        return []
    except KeyError as e:
        log.error("Missing expected column in the CSV file: %s", e)
        return []
    except AttributeError:
        log.error("The 'Guest Name' column does not contain string values.")
        return []
    except TypeError as e:
        log.error("Type error occurred: %s", e)
        return []


def extract_data(file_name):
    """Extracts user data from a CSV file.

    This function reads a CSV file to retrieve user information,
    specifically extracting the first name, last name, and email from the
    "Guest Name" and "Guest Email" columns. It processes the data to ensure
    that names are split correctly and returns a structured list of
    dictionaries containing the relevant information.

    Args:
        file_name (str): The path to the CSV file to read.

    Returns:
        list of dict: A list of dictionaries containing 'First Name',
            'Last Name', and 'Guest Email'.
    """

    # Read the CSV file using Pandas
    df = pd.read_csv(file_name)

    log.debug("Parsing csv")

    # Split the 'Guest Name' into 'First Name' and 'Last Name'
    df[["First Name", "Last Name"]] = df["Guest Name"].str.split(
        n=1, expand=True
    )

    # Fill empty 'Last Name' fields with an empty string
    df["Last Name"] = df["Last Name"].fillna("")

    # Create a list of dictionaries containing the needed information
    data = df[["First Name", "Last Name", "Guest Email"]].to_dict(
        orient="records"
    )

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


def create_vce_user(user_info_list, api_token=TOKEN):
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
            "x-verkada-auth": api_token,
        }
        csrf_token, user_token, user_id = None, None, None

        try:
            # Initialize the user session.
            if USERNAME and PASSWORD and ORG_ID:
                csrf_token, user_token, user_id = login_and_get_tokens(
                    session,
                    USERNAME,
                    PASSWORD,
                    ORG_ID,
                    TOTP,
                )
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

                    grant_org_admin(
                        csrf_token, user_id, data["user_id"], session
                    )

                return emails

            # Handles when the required credentials were not received
            else:
                log.critical(
                    "No credentials were provided during "
                    "the authentication process or audit log "
                    "could not be retrieved."
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
