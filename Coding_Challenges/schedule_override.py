"""
Author: Ian Young
Purpose: Opens doors both literally and figuratively
"""

from datetime import datetime, timedelta
from os import getenv

import requests
from dotenv import load_dotenv

from tools import (
    log,
    login_and_get_tokens,
    logout,
    custom_exceptions,
    SharedParams,
)

load_dotenv()

# User logging credentials
USERNAME = getenv("")
PASSWORD = getenv("")
ORG_ID = getenv("")

UNLOCK_PERIOD = 5  # Change this integer to change override time (minutes).
VIRTUAL_DEVICE = "5eff4677-974d-44ca-a6ba-fb7595265e0a"  # String or list


def schedule_override(params: SharedParams, door, time):
    """
    Sets a schedule override for the given door(s) inside of Verkada Command
    with a valid Command user session. The schedule override event will
    appear in the audit logs.

    :param params: Class with commonly used variables
    :type params: SharedParams
    :param door: The target door ID
    :type: str, list[str]
    :param time: The length of the override in minutes
    :type time: int
    """
    url = f"https://vcerberus.command.verkada.com/organizations/{params.org_id}/schedules"
    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    end_time = (datetime.now() + timedelta(minutes=time)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    try:
        # Check to see if a list of doors was given
        log.debug("Checking if a list was provided.")

        if isinstance(door, list):
            log.debug("List provided -> Checking if list is iterable.")

            if hasattr(door, "__iter__"):
                log.debug(
                    "List provided -> list is iterable -> attempting unlocks."
                )

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
                            "defaultDoorLockState": "UNLOCKED",
                        }
                    ],
                }

                log.debug("Unlocking virtual devices: %s.", door)
                response = params.session.post(url, headers=headers, json=data)
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
                        "defaultDoorLockState": "UNLOCKED",
                    }
                ],
            }
            log.debug("Unlocking %s.", door)
            response = params.session.post(url, headers=headers, json=data)
            response.raise_for_status()

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "schedule override"
        ) from e


if __name__ == "__main__":
    with requests.Session() as override_session:
        try:
            log.debug("Retrieving credentials.")
            if USERNAME and PASSWORD and ORG_ID:
                csrf_token, user_token, user_id = login_and_get_tokens(
                    override_session, USERNAME, PASSWORD, ORG_ID
                )

                if csrf_token and user_token and user_id:
                    log.debug("Credentials retrieved.")
                    runtime_params = SharedParams(
                        override_session,
                        csrf_token,
                        user_token,
                        user_id,
                        ORG_ID,
                    )
                    schedule_override(
                        runtime_params,
                        VIRTUAL_DEVICE,
                        UNLOCK_PERIOD,
                    )
                    log.debug("All door(s) unlocked.")

            else:
                log.warning("Did not receive the necessary credentials.")

        except KeyboardInterrupt:
            log.warning("Keyboard interrupt detected. Exiting...")

        finally:
            if ORG_ID and "csrf_token" in locals():
                logout(override_session, csrf_token, user_token, ORG_ID)
            override_session.close()
