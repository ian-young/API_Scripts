# Author: Ian Young
# Purpose: Opens doors both literally and figuratively

import creds
import requests
import logging
from datetime import datetime, timedelta

log = logging.getLogger()
log.setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s"
)

LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
UNLOCK_PERIOD = 5  # Change this integer to change override time (minutes).


def login_and_get_tokens(username, password, org_id):
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
        response = session.post(LOGIN_URL, json=login_data)
        response.raise_for_status()

        # Extract relevant information from the JSON response
        json_response = response.json()
        csrf_token = json_response.get("csrfToken")
        user_token = json_response.get("userToken")
        user_id = json_response.get("userId")

        return csrf_token, user_token, user_id

    # Handle exceptions
    except requests.exceptions.Timeout:
        return None, None, None

    except requests.exceptions.TooManyRedirects:
        return None, None, None

    except requests.exceptions.HTTPError:
        return None, None, None

    except requests.exceptions.ConnectionError:
        return None, None, None

    except requests.exceptions.RequestException:
        return None, None, None

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")
        session.close()


def schedule_override(x_verkada_token, x_verkada_auth, usr, org_id, door, time):
    """
    Unlocks the given door(s) inside of Verkada Command with a valid Command
    user session. The door unlock event will appear as a remote unlock in the
    audit logs.

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

                log.debug(f"Unlocking virutal devices: {door}.")
                response = session.post(url, headers=headers, json=data)
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
            log.debug(f"Unlocking {door}.")
            response = session.post(url, headers=headers, json=data)
            response.raise_for_status()

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
        print("Keyboard interrupt detected. Exiting...")
        session.close()


if __name__ == "__main__":
    try:
        with requests.Session() as session:
            log.debug("Retrieving credentials.")
            csrf_token, user_token, user_id = login_and_get_tokens(
                creds.slc_username, creds.slc_password, creds.slc_id)

            if csrf_token and user_token and user_id:
                log.debug("Credentials retrieved.")
                schedule_override(csrf_token, user_token, user_id,
                                  creds.slc_id,
                                  "5eff4677-974d-44ca-a6ba-fb7595265e0a", UNLOCK_PERIOD)
                log.debug("All door(s) unlocked.")

            else:
                log.warning("Did not receive the necessary credentials.")

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")
