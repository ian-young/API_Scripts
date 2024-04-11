import requests
import logging
import time
import gatherDevices  # TODO: Need to adjust to pull IDs and not serials
from os import getenv
from dotenv import load_dotenv

log = logging.getLogger()
log.setLevel(logging.DEBUG)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s"
)

load_dotenv()

USERNAME = getenv("lab_username")
PASSWORD = getenv("lab_password")
ORG_ID = getenv("LAB_ID")

# Root API URL
ROOT = "https://api.command.verkada.com/vinter/v1/user/async"
SHARD = "?sharding=true"
# Set final, global URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"
# Parameter is cameraId
CAMERA_DECOM = "https://vprovision.command.verkada.com/camera/decommission"
# Parameters are deviceId and organizationId
AKEYPADS_DECOM = "https://alarms.command.verkada.com/device/keypad_hub/decommission"
# Parameters: deviceId, deviceType: "doorContactSensor" and organizationId
ASENSORS_DECOM = "https://alarms.command.verkada.com/device/sensor/delete"
# Parameters: deviceId and organizationId
APANEL_DECOM = "https://alarms.command.verkada.com/device/hub/decommission"
# Parameters: devicceId
ENVIRONMENTAL_DECOM = "https://vsensor.command.verkada.com/devices/decommission"
# DELETE, not POST (works with desk station, too)
INTERCOM_DECOM = f"{ROOT}/organization/{ORG_ID}/device/{placeholder}{SHARD}"
# DELETE, not POST
GUEST_IPADS = f"https://vdoorman.command.verkada.com/device/org/{ORG_ID}/site/{site_id}?deviceId={device_id}"
DELETE_PRINTER = f"https://vdoorman.command.verkada.com/printer/org/{ORG_ID}/site/{site_id}?printerId={printer_id}"


def login_and_get_tokens(username=USERNAME, password=PASSWORD, org_id=ORG_ID):
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
        log.debug("Requesting session.")
        response = session.post(LOGIN_URL, json=login_data)
        response.raise_for_status()
        log.debug("Session opened.")

        # Extract relevant information from the JSON response
        log.debug("Parsing JSON response.")
        json_response = response.json()
        csrf_token = json_response.get("csrfToken")
        user_token = json_response.get("userToken")
        user_id = json_response.get("userId")
        log.debug("Response parsed. Returning values.")

        return csrf_token, user_token, user_id

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None, None, None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects. Aborting...")
        return None, None, None

    except requests.exceptions.HTTPError:
        log.error(
            f"Returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None, None, None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None, None, None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None, None, None


def logout(x_verkada_token, x_verkada_auth, org_id=ORG_ID):
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
        response = session.post(LOGOUT_URL, headers=headers, json=body)
        response.raise_for_status()

        log.info("Logging out.")

    except requests.exceptions.Timeout:
        log.error("The request has timed out.")

    except requests.exceptions.TooManyRedirects:
        log.error("Too many HTTP redirects.")

    except requests.HTTPError as e:
        log.error(f"An error has occured: {e}")

    except requests.exceptions.ConnectionError:
        log.error("Error connecting to the server.")

    except requests.exceptions.RequestException:
        log.error("API error.")

    except KeyboardInterrupt:
        log.warning("Keyboard interrupt detected. Exiting...")

    finally:
        session.close()


def deleteCameras(x_verkada_token, x_verkada_auth, usr,
                  org_id=ORG_ID):
    body = {
        "organizationId": org_id
    }

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting cameras.")
        cameras = gatherDevices.list_cameras(x_verkada_token, x_verkada_auth,
                                             usr, org_id)
        if cameras:
            for camera in cameras:
                params = {
                    "deviceId": camera['deviceId']
                }

                response = session.post(
                    CAMERA_DECOM, json=body, headers=headers, params=params)
                response.raise_for_status()  # Raise an exception for HTTP errors

            log.debug("Cameras deleted.")

        else:
            log.warning("No cameras were received.")

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Desk stations returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


def deleteKeypads(x_verkada_token, x_verkada_auth, usr,
                  org_id=ORG_ID):
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting Alarm keypads.")
        keypads = gatherDevices.list_cameras(x_verkada_token, x_verkada_auth,
                                             usr, org_id)
        if keypads:
            for keypad in keypads:
                params = {
                    "deviceId": keypad['deviceId'],
                    "organizationId": org_id
                }

                response = session.post(
                    AKEYPADS_DECOM, headers=headers, params=params)
                response.raise_for_status()  # Raise an exception for HTTP errors

            log.debug("Keypads deleted.")

        else:
            log.warning("No keypads were received.")

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Desk stations returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


def deleteSensors(x_verkada_token, x_verkada_auth, usr,
                  org_id=ORG_ID):
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting Alarm sensors.")
        sensors = gatherDevices.list_cameras(x_verkada_token, x_verkada_auth,
                                             usr, org_id)
        if sensors:
            # TODO: Need to grab sensor type from JSON
            for sensor in sensors:
                params = {
                    "deviceId": sensor['deviceId'],
                    "organizationId": org_id
                }

                response = session.post(
                    ASENSORS_DECOM, headers=headers, params=params)
                response.raise_for_status()  # Raise an exception for HTTP errors

            log.debug("Alarm sensors deleted.")

        else:
            log.warning("No Alarm sensors were received.")

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Desk stations returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


# TODO: Adjust accordingly.
def deletePanels(x_verkada_token, x_verkada_auth, usr,
                 org_id=ORG_ID):
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting Alarm panels.")
        panels = gatherDevices.list_cameras(x_verkada_token, x_verkada_auth,
                                            usr, org_id)
        if panels:
            for panel in panels:
                params = {
                    "deviceId": panel['deviceId'],
                    "organizationId": org_id
                }

                response = session.post(
                    CAMERA_DECOM, headers=headers, params=params)
                response.raise_for_status()  # Raise an exception for HTTP errors

            log.debug("Alarm panels deleted.")

        else:
            log.warning("No Alarm panels were received.")

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Desk stations returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


# TODO: Adjust accordingly.
def deleteEnvironmental(x_verkada_token, x_verkada_auth, usr,
                        org_id=ORG_ID):
    body = {
        "organizationId": org_id
    }

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting cameras.")
        cameras = gatherDevices.list_cameras(x_verkada_token, x_verkada_auth,
                                             usr, org_id)
        if cameras:
            for camera in cameras:
                params = {
                    "deviceId": camera['deviceId']
                }

                response = session.post(
                    CAMERA_DECOM, json=body, headers=headers, params=params)
                response.raise_for_status()  # Raise an exception for HTTP errors

            log.debug("Cameras deleted.")

        else:
            log.warning("No cameras were received.")

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Desk stations returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


# TODO: Adjust accordingly.
def deleteIntercom(x_verkada_token, x_verkada_auth, usr,
                   org_id=ORG_ID):
    body = {
        "organizationId": org_id
    }

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting cameras.")
        cameras = gatherDevices.list_cameras(x_verkada_token, x_verkada_auth,
                                             usr, org_id)
        if cameras:
            for camera in cameras:
                params = {
                    "deviceId": camera['deviceId']
                }

                # TODO: Change to DELETE instead of POST
                response = session.post(
                    CAMERA_DECOM, json=body, headers=headers, params=params)
                response.raise_for_status()  # Raise an exception for HTTP errors

            log.debug("Cameras deleted.")

        else:
            log.warning("No cameras were received.")

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Desk stations returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


if __name__ == '__main__':
    with requests.Session as session:
        start_run_time = time.time()  # Start timing the script
        with requests.Session() as session:
            try:
                # Initialize the user session.
                csrf_token, user_token, user_id = login_and_get_tokens()

                # Continue if the required information has been received
                if csrf_token and user_token and user_id:
                    pass
                # Handles when the required credentials were not received
                else:
                    log.critical(
                        f"No credentials were provided during "
                        f"the authentication process or audit log "
                        f"could not be retrieved."
                    )

                # Calculate the time take to run and post it to the log
                elapsed_time = time.time() - start_run_time
                log.info("-------")
                log.info(f"Total time to complete {elapsed_time:.2f}")

            # Gracefully handle an interrupt
            except KeyboardInterrupt:
                print(f"\nKeyboard interrupt detected. Logging out & aborting...")

            finally:
                if csrf_token and user_token:
                    log.debug("Logging out.")
                    logout(csrf_token, user_token)
                session.close()
                log.debug("Session closed.\nExiting...")
