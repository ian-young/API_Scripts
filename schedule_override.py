"""
Author: Ian Young
Purpose: Opens doors both literally and figuratively
"""

import logging
from datetime import datetime, timedelta
from os import getenv

import requests
from dotenv import load_dotenv

import custom_exceptions
from verkada_totp import generate_totp

load_dotenv()

log = logging.getLogger()
log.setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Static URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"

# User loging credentials
USERNAME = getenv("")
PASSWORD = getenv("")
ORG_ID = getenv("")

UNLOCK_PERIOD = 5  # Change this integer to change override time (minutes).
VIRTUAL_DEVICE = "5eff4677-974d-44ca-a6ba-fb7595265e0a"  # String or list


def login_and_get_tokens(login_session, username, password, org_id):
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
        "otp": generate_totp(getenv("lab_totp")),
        "org_id": org_id
    }

    try:
        # Request the user session
        response = login_session.post(LOGIN_URL, json=login_data)
        response.raise_for_status()

        # Extract relevant information from the JSON response
        json_response = response.json()
        session_csrf_token = json_response.get("csrfToken")
        session_user_token = json_response.get("userToken")
        session_user_id = json_response.get("userId")

        return session_csrf_token, session_user_token, session_user_id

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(e, response, "Log in")


def logout(logout_session, x_verkada_token, x_verkada_auth, org_id=ORG_ID):
    """
    Logs the Python script out of Command to prevent orphaned sessions.

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


def schedule_override(schedule_session, x_verkada_token, x_verkada_auth, usr,
                      org_id, door, time):
    """
    Sets a schedule override for the given door(s) inside of Verkada Command 
    with a valid Command user session. The schedule overrride event will 
    appear in the audit logs.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param org_id: The Verkada organization ID of the target org.
    :type org_id: str
    :param door: The target door ID
    :type: str, list[str]
    :param time: The length of the override in minutes
    :type time: int
    """
    url = f"https://vcerberus.command.verkada.com/organizations/{org_id}/schedules"
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    end_time = (datetime.now() + timedelta(minutes=time)
                ).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        # Check to see if a list of doors was given
        log.debug("Checking if a list was provided.")

        if isinstance(door, list):
            log.debug("List provided -> Checking if list is iterable.")

            if hasattr(door, "__iter__"):
                log.debug(
                    "List provided -> list is iterable -> attempting unlocks.")

                data = {
                    "sitesEnabled": True,
                    "schedules": [
                        {
                            "priority": "MANUAL",
                            "startDateTime": current_time,
                            "endDateTime": end_time,
                            "deleted": False,
                            "name": "",
                            "type": "DOOR",
                            "doors": door,
                            "events": [],
                            "defaultDoorLockState": "UNLOCKED"
                        }
                    ]
                }

                log.debug("Unlocking virutal devices: %s.", door)
                response = schedule_session.post(url, headers=headers, json=data)
                response.raise_for_status()

            else:
                log.critical("List is not iterable.")

        # Run for a single door
        else:
            data = {
                "sitesEnabled": True,
                "schedules": [
                    {
                        "priority": "MANUAL",
                        "startDateTime": current_time,
                        "endDateTime": end_time,
                        "deleted": False,
                        "name": "",
                        "type": "DOOR",
                        "doors": [str(door)],
                        "events": [],
                        "defaultDoorLockState": "UNLOCKED"
                    }
                ]
            }
            log.debug("Unlocking %s.", door)
            response = schedule_session.post(url, headers=headers, json=data)
            response.raise_for_status()

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(e, response, "schedule override")


if __name__ == "__main__":
    with requests.Session() as session:
        try:
            log.debug("Retrieving credentials.")
            csrf_token, user_token, user_id = login_and_get_tokens(
                session, USERNAME, PASSWORD, ORG_ID)

            if csrf_token and user_token and user_id:
                log.debug("Credentials retrieved.")
                schedule_override(session, csrf_token, user_token, user_id,
                                  ORG_ID, VIRTUAL_DEVICE, UNLOCK_PERIOD)
                log.debug("All door(s) unlocked.")

                logout(session, csrf_token, user_token)

            else:
                log.warning("Did not receive the necessary credentials.")
                session.close()

        except KeyboardInterrupt:
            log.warning("Keyboard interrupt detected. Exiting...")

        finally:
            session.close()
