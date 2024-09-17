"""
Author: Ian Young
Purpose: Opens lockdowns both literally and figuratively
"""

# Import essential libraries
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

load_dotenv()  # Load credentials file

# User logging credentials
USERNAME = getenv("")
PASSWORD = getenv("")
ORG_ID = getenv("")

LOCKDOWN_ID = "9884e9b2-1871-4aaf-86d7-0dc12b4ff024"  # String or list


##############################################################################
#################################  Requests  #################################
##############################################################################


def trigger_lockdown(params: SharedParams, lockdown_id):
    """
    Triggers the given lockdown(s) inside of Verkada Command with a valid Command
    user session. The lockdown trigger event will appear as a remote trigger in the
    audit logs.

    :param params: A class with frequently used variable when making
        requests.
    :type params: SharedParams
    :param lockdown_id: The id of the lockdown to trigger.
    :type lockdown_id: str, list[str]
    """
    url = f"https://vcerberus.command.verkada.com/organizations/{params.org_id}/lockdowns/trigger"
    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }
    try:
        # Check to see if a list of lockdowns was given
        log.debug("Checking if a list was provided.")

        if isinstance(lockdown_id, list):
            log.debug("List provided -> Checking if list is iterable.")

            if hasattr(lockdown_id, "__iter__"):
                log.debug(
                    "List provided -> list is iterable -> attempting triggers."
                )

                for target in lockdown_id:
                    body = {"lockdownId": target}

                    log.debug("triggering lockdown: %s.", target)
                    response = params.session.post(
                        url, headers=headers, json=body
                    )
                    response.raise_for_status()

            else:
                log.critical("List is not iterable.")

        # Run for a single lockdown
        else:
            body = {"lockdownId": lockdown_id}

            log.debug("triggering %s.", lockdown_id)
            response = params.session.post(url, headers=headers, json=body)
            response.raise_for_status()

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Lockdown"
        ) from e


if __name__ == "__main__":
    try:
        with requests.Session() as lockdown_session:
            log.debug("Retrieving credentials.")
            if USERNAME and PASSWORD and ORG_ID:
                csrf_token, user_token, user_id = login_and_get_tokens(
                    lockdown_session, USERNAME, PASSWORD, ORG_ID
                )

                if csrf_token and user_token and user_id:
                    log.debug("Credentials retrieved.")
                    runtime_params = SharedParams(
                        lockdown_session,
                        csrf_token,
                        user_token,
                        user_id,
                        ORG_ID,
                    )
                    trigger_lockdown(
                        runtime_params,
                        LOCKDOWN_ID,
                    )
                    log.debug("All lockdowns triggered.")

            else:
                log.warning("Did not receive the necessary credentials.")

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")

    finally:
        if ORG_ID and "csrf_token" in locals():
            logout(lockdown_session, csrf_token, user_token, ORG_ID)
        lockdown_session.close()
