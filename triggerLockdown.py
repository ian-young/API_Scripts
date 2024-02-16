# Author: Ian Young
# Purpose: Opens lockdowns both literally and figuratively

import creds
import requests
import logging

log = logging.getLogger()
log.setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s"
)

# Static URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"

# User loging credentials
USERNAME = creds.slc_username
PASSWORD = creds.slc_password
ORG_ID = creds.slc_id

LOCKDOWN_ID = "9884e9b2-1871-4aaf-86d7-0dc12b4ff024"  # String or list


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
        session.close()
        return None, None, None

    except requests.exceptions.TooManyRedirects:
        session.close()
        return None, None, None

    except requests.exceptions.HTTPError:
        session.close()
        return None, None, None

    except requests.exceptions.ConnectionError:
        session.close()
        return None, None, None

    except requests.exceptions.RequestException:
        session.close()
        return None, None, None

    except KeyboardInterrupt:
        log.warning("Keyboard interrupt detected. Exiting...")
        session.close()


def logout(x_verkada_token, x_verkada_auth, org_id=ORG_ID):
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "x-verkada-orginization": org_id
    }

    body = {
        "logoutCurrentEmailOnly": True
    }
    try:
        log.info("Logging out")
        response = session.post(LOGOUT_URL, headers=headers, json=body)
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
        log.warning("Keyboard interrupt detected. Exiting...")

    finally:
        session.close()


def trigger_lockdown(x_verkada_token, x_verkada_auth, usr, org_id, lockdown_id):
    """
    Triggers the given lockdown(s) inside of Verkada Command with a valid Command
    user session. The lockdown trigger event will appear as a remote trigger in the
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
    :param lockdown_id: The id of the lockdown to trigger.
    :type lockdown_id: str, list[str]
    """
    url = f"https://vcerberus.command.verkada.com/organizations/{org_id}/lockdowns/trigger"
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }
    try:
        # Check to see if a list of lockdowns was given
        log.debug("Checking if a list was provided.")

        if isinstance(lockdown_id, list):
            log.debug("List provided -> Checking if list is iterable.")

            if hasattr(lockdown_id, "__iter__"):
                log.debug(
                    "List provided -> list is iterable -> attempting triggers.")

                for target in lockdown_id:
                    body = {
                        "lockdownId": target
                    }

                    log.debug(f"triggering lockdown: {target}.")
                    response = session.post(url, headers=headers, json=body)
                    response.raise_for_status()

            else:
                log.critical("List is not iterable.")

        # Run for a single lockdown
        else:
            body = {
                "lockdownId": lockdown_id
            }

            log.debug(f"triggering {lockdown_id}.")
            response = session.post(url, headers=headers, json=body)
            response.raise_for_status()

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error("The request has timed out.")
        logout(csrf_token, user_token)
        session.close()

    except requests.exceptions.TooManyRedirects:
        log.error("Too many HTTP redirects.")
        logout(csrf_token, user_token)
        session.close()

    except requests.HTTPError as e:
        log.error(f"An error has occured\n{e}")
        logout(csrf_token, user_token)
        session.close()

    except requests.exceptions.ConnectionError:
        log.error("Error connecting to the server.")
        logout(csrf_token, user_token)
        session.close()

    except requests.exceptions.RequestException:
        log.error("API error.")
        logout(csrf_token, user_token)
        session.close()

    except KeyboardInterrupt:
        log.warning("Keyboard interrupt detected. Exiting...")
        logout(csrf_token, user_token)
        session.close()


if __name__ == "__main__":
    try:
        with requests.Session() as session:
            log.debug("Retrieving credentials.")
            csrf_token, user_token, user_id = login_and_get_tokens(
                USERNAME, PASSWORD, ORG_ID)

            if csrf_token and user_token and user_id:
                log.debug("Credentials retrieved.")
                trigger_lockdown(csrf_token, user_token, user_id,
                                 ORG_ID, LOCKDOWN_ID)
                log.debug("All lockdowns triggered.")

                logout(csrf_token, user_token)

            else:
                log.warning("Did not receive the necessary credentials.")

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")

    finally:
        session.close()
