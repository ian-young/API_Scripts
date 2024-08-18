import logging
from os import getenv

import requests
import pandas as pd
from dotenv import load_dotenv

from QoL.authentication import login_and_get_tokens, logout
from QoL.api_endpoints import PROMOTE_ORG_ADMIN, CREATE_USER
from QoL.custom_exceptions import APIExceptionHandler

log = logging.getLogger()
LOG_LEVEL = logging.INFO
log.setLevel(LOG_LEVEL)
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s - %(levelname)s: %(message)s")

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

load_dotenv()  # Import credentials

ORG_ID = getenv("boi_id")
USERNAME = getenv("boi_username")
PASSWORD = getenv("boi_password")
TOTP = getenv("boi_totp")
API_KEY = getenv("boi_key")
FILE_PATH = ("/Users/ian.young/Documents/.scripts/API_Scripts/VCE/VCE_AC_Specialist_Check_ins_GuestLog - 2024-07-16 "
             "2.csv")


def read_csv(file_name):
    df = pd.read_csv(file_name)
    df[['First Name', 'Last Name']] = df['Guest Name'].str.split(expand=True)
    df['Guest Email'] = df['Guest Email'].fillna('')
    return df[['First Name', 'Last Name', 'Guest Email']].to_dict(orient='records')


def grant_org_admin(x_verkada_token, usr_id, target_id, management_session, org_id=ORG_ID):
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
        response = management_session.post(PROMOTE_ORG_ADMIN, headers=headers, json=body, timeout=3)
        response.raise_for_status()
        log.debug("Request passed.")

    except requests.exceptions.RequestException as e:
        raise APIExceptionHandler(e, response, "Promote org admin") from e


def create_vce_user(user_info_list, api_key=API_KEY):
    log.debug("User list:\n%s", user_info_list)
    csrf_token, user_token, user_id = None, None, None

    with requests.Session() as session:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": api_key,
        }

        try:
            csrf_token, user_token, user_id = login_and_get_tokens(session, USERNAME, PASSWORD, TOTP, ORG_ID)

            for result in user_info_list:
                body = {
                    "first_name": result["First Name"],
                    "last_name": result["Last Name"],
                    "email": result["Guest Email"],
                }

                response = session.post(CREATE_USER, headers=headers, json=body, timeout=3)

                if response.status_code != 500:
                    response.raise_for_status()
                else:
                    log.warning("User already exists. Skipping.")
                    continue

                data = response.json()
                log.info(
                    "User %s %s has been successfully created. An email has been sent to %s.",
                    result["First Name"],
                    result["Last Name"],
                    result["Guest Email"],
                )

                grant_org_admin(csrf_token, user_id, data["user_id"], session)

        except requests.exceptions.RequestException as e:
            raise APIExceptionHandler(e, response, "Create user") from e

        finally:
            if user_id and user_token:
                logout(session, csrf_token, user_id, ORG_ID)
            session.close()
            log.info("Session closed.\nExiting...")


create_vce_user(read_csv(FILE_PATH))