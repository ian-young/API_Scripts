import requests
import logging
import threading
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
ORG_ID = getenv("lab_id")

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
# Parameters: deviceId
ENVIRONMENTAL_DECOM = "https://vsensor.command.verkada.com/devices/decommission"
# DELETE, not POST (works with desk station, too)
# INTERCOM_DECOM = f"{ROOT}/organization/{ORG_ID}/device/{placeholder}{SHARD}"
# DELETE, not POST
# GUEST_IPADS = f"https://vdoorman.command.verkada.com/device/org/{ORG_ID}/site/{site_id}?deviceId={device_id}"
# DELETE_PRINTER = f"https://vdoorman.command.verkada.com/printer/org/{ORG_ID}/site/{site_id}?printerId={printer_id}"


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


##############################################################################
##############################################################################


def deleteCameras(x_verkada_token, x_verkada_auth, usr,
                  org_id=ORG_ID):
    """
    
    """
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
                    "deviceId": camera
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


def deleteSensors(x_verkada_token, x_verkada_auth, usr,
                  org_id=ORG_ID):
    threads = []

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    def delete_sensor(device_dict):
        for device in device_dict:
            params = {
                "deviceId": device.get("deviceId"),
                "organizationId": org_id,
                "deviceType": device.get("deviceType")
            }
            try:
                response = session.post(
                    ASENSORS_DECOM, headers=headers, params=params)
                response.raise_for_status()  # Raise an exception for HTTP errors

                log.debug(f"Deleted wireless sensor: {
                          device.get('deviceType')}"
                          )

            # Handle exceptions
            except requests.exceptions.Timeout:
                log.error(f"Connection timed out.")
                return None

            except requests.exceptions.TooManyRedirects:
                log.error(f"Too many redirects.\nAborting...")
                return None

            except requests.exceptions.HTTPError:
                log.error(
                    f"Wireless alarm sensor returned with a non-200 code: "
                    f"{response.status_code}"
                )
                return None

            except requests.exceptions.ConnectionError:
                log.error(f"Error connecting to the server.")
                return None

            except requests.exceptions.RequestException as e:
                log.error(f"Verkada API Error: {e}")
                return None

    def delete_keypads(device_ids):
        for device_id in device_ids:
            params = {
                "deviceId": device_id,
                "organizationId": org_id
            }

            try:
                response = session.post(
                    AKEYPADS_DECOM, headers=headers, params=params)
                response.raise_for_status()  # Raise an exception for HTTP errors

                log.debug("Keypad deleted.")

            # Handle exceptions
            except requests.exceptions.Timeout:
                log.error(f"Connection timed out.")
                return None

            except requests.exceptions.TooManyRedirects:
                log.error(f"Too many redirects.\nAborting...")
                return None

            except requests.exceptions.HTTPError:
                log.error(
                    f"Alarm keypad returned with a non-200 code: "
                    f"{response.status_code}"
                )
                return None

            except requests.exceptions.ConnectionError:
                log.error(f"Error connecting to the server.")
                return None

            except requests.exceptions.RequestException as e:
                log.error(f"Verkada API Error: {e}")
                return None

    def convert_to_dict(array, deviceType):
        device_dict = []

        for device in array:
            device_dict_value = {
                "deviceId": device,
                "deviceType": deviceType
            }
            device_dict.append(device_dict_value)

        return device_dict

    # Request all alarm sensors
    log.debug("Requesting alarm sensors.")
    dcs, gbs, hub, ms, pb, ws, wr = gatherDevices.list_Alarms(
        x_verkada_token, x_verkada_auth, usr, org_id)

    # Check if it is empty, if so, skip. If not, turn it into a dictionary.
    if dcs:
        door_thread = threading.Thread(target=delete_sensor, args=(
            convert_to_dict(dcs, "doorContactSensor")))
        threads.append(door_thread)
    if gbs:
        glass_thread = threading.Thread(target=delete_sensor, args=(
            convert_to_dict(gbs, "glassBreakSensor")))
        threads.append(glass_thread)
    if hub:
        keypad_thread = threading.Thread(target=delete_keypads, args=(hub))
        threads.append(keypad_thread)
    if ms:
        motion_thread = threading.Thread(target=delete_sensor, args=(
            convert_to_dict(ms, "motionSensor")))
        threads.append(motion_thread)
    if pb:
        panic_thread = threading.Thread(target=delete_sensor, args=(
            convert_to_dict(pb, "panicButton")))
        threads.append(panic_thread)
    if ws:
        water_thread = threading.Thread(target=delete_sensor, args=(
            convert_to_dict(ws, "waterSensor")))
        threads.append(water_thread)
    if wr:
        relay_thread = threading.Thread(target=delete_sensor, args=(
            convert_to_dict(wr, "wirelessRelay")))
        threads.append(relay_thread)

    # Check if there are threads waiting to be ran.
    if threads:
        # Run the threads
        for thread in threads:
            thread.start()
        # Wait for them to finish
        for thread in threads:
            thread.join()

        log.debug("Alarm sensors deleted.")

    else:
        log.warning("No alarm sensors were received.")


# TODO: Add to gatherDevices.py
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
            f"Alarm panels returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


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
        log.debug("Requesting environmental sensors.")
        sv_ids = gatherDevices.list_Sensors(x_verkada_token, x_verkada_auth,
                                            usr, org_id)
        if sv_ids:
            for sensor in sv_ids:
                params = {
                    "deviceId": sensor
                }

                response = session.post(
                    ENVIRONMENTAL_DECOM,
                    json=body,
                    headers=headers,
                    params=params
                )
                response.raise_for_status()  # Raise an exception for HTTP errors

            log.debug("Environmental sensors deleted.")

        else:
            log.warning("No environmental sensors were received.")

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Environmental sensors returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


# TODO: Adjust accordingly and find endpoint that lists intercoms.
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