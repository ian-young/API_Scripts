import requests
import logging
import threading
import time
from datetime import datetime
from dotenv import load_dotenv
from os import getenv
from colorama import Fore, Style

colorama.init(autoreset=True)  # Initialize colorized output

load_dotenv()  # Load credentials file

log = logging.getLogger()
log.setLevel(logging.INFO)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

load_dotenv()

USERNAME = getenv()
PASSWORD = getenv()
ORG_ID = getenv()
API_KEY = getenv()

# Root API URL
ROOT = "https://api.command.verkada.com/vinter/v1/user/async"
SHARD = "?sharding=true"


# Set final, global URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"
CAMERA_DECOM = "https://vprovision.command.verkada.com/camera/decommission"
AKEYPADS_DECOM = "https://alarms.command.verkada.com/device/keypad_hub/decommission"
ASENSORS_DECOM = "https://alarms.command.verkada.com/device/sensor/delete"
APANEL_DECOM = "https://alarms.command.verkada.com/device/hub/decommission"
ENVIRONMENTAL_DECOM = "https://vsensor.command.verkada.com/devices/decommission"
ACCESS_DECOM = "https://vcerberus.command.verkada.com/access_device/decommission"
# DELETE, not POST (works with desk station, too)
# INTERCOM_DECOM = f"{ROOT}/organization/{ORG_ID}/device/{placeholder}{SHARD}"
# DELETE, not POST
# GUEST_IPADS = f"https://vdoorman.command.verkada.com/device/org/{ORG_ID}/site/{site_id}?deviceId={device_id}"
# DELETE_PRINTER = f"https://vdoorman.command.verkada.com/printer/org/{ORG_ID}/site/{site_id}?printerId={printer_id}"


##############################################################################
                            #   Authentication   #
##############################################################################


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
        log.error(f"{Fore.RED}Connection timed out.{Style.RESET_ALL}")
        return None, None, None

    except requests.exceptions.TooManyRedirects:
        log.error(f"{Fore.RED}Too many redirects. Aborting..."
                  f"{Style.RESET_ALL}"
                  )
        return None, None, None

    except requests.exceptions.HTTPError:
        log.error(
            f"{Fore.RED}Log in returned with a non-200 code: "
            f"{response.status_code}{Style.RESET_ALL}"
        )
        return None, None, None

    except requests.exceptions.ConnectionError:
        log.error(
            f"{Fore.RED}"
            f"Error connecting to the server."
            f"{Style.RESET_ALL}"
        )
        return None, None, None

    except requests.exceptions.RequestException as e:
        log.error(f"{Fore.RED}Verkada API Error:{Style.RESET_ALL} {e}")
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
        log.error(f"{Fore.RED}The request has timed out.{Style.RESET_ALL}")

    except requests.exceptions.TooManyRedirects:
        log.error(f"{Fore.RED}Too many HTTP redirects.{Style.RESET_ALL}")

    except requests.HTTPError as e:
        log.error(f"{Fore.RED}An error has occured:{Style.RESET_ALL} {e}")

    except requests.exceptions.ConnectionError:
        log.error(f"{Fore.RED}Error connecting to the server."
                  f"{Style.RESET_ALL}"
                  )

    except requests.exceptions.RequestException:
        log.error(f"{Fore.RED}API error.{Style.RESET_ALL}")

    except KeyboardInterrupt:
        log.warning(
            f"{Fore.MAGENTA}"
            f"Keyboard interrupt detected. Exiting..."
            f"{Style.RESET_ALL}"
        )

    finally:
        session.close()


##############################################################################
                            #   Requests   #
##############################################################################


def deleteCameras(x_verkada_token, x_verkada_auth, usr):
    """
    Deletes all cameras from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada 
    session.
    :type x_verkada_auth: str
    :param usr: The user ID of the authenticated user for a valid Verkada
    Command session.
    :type usr: str
    """
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting cameras.")
        cameras = gatherDevices.list_cameras(API_KEY, session)

        if cameras:
            for camera in cameras:
                body = {
                    "cameraId": camera
                body = {
                    "cameraId": camera
                }
                print(camera)
                response = session.post(
                    CAMERA_DECOM, headers=headers, json=body)
                    CAMERA_DECOM, headers=headers, json=body)
                response.raise_for_status()  # Raise an exception for HTTP errors

            log.info(f"{Fore.GREEN}Cameras deleted.{Style.RESET_ALL}")

        else:
            log.warning(
                f"{Fore.MAGENTA}"
                f"No cameras were received."
                f"{Style.RESET_ALL}"
            )

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"{Fore.RED}Connection timed out.{Style.RESET_ALL}")

    except requests.exceptions.TooManyRedirects:
        log.error(
            f"{Fore.RED}"
            f"Too many redirects. Aborting..."
            f"{Style.RESET_ALL}"
        )

    except requests.exceptions.HTTPError:
        log.error(
            f"Delete camera returned with a non-200 code: "
            f"{response.status_code}"
        )

    except requests.exceptions.ConnectionError:
        log.error(
            f"{Fore.RED}"
            f"Error connecting to the server."
            f"{Style.RESET_ALL}"
        )

    except requests.exceptions.RequestException as e:
        log.error(f"{Fore.RED}Verkada API Error:{Style.RESET_ALL} {e}")


def deleteSensors(x_verkada_token, x_verkada_auth, usr, session,
                  org_id=ORG_ID):
    """
    Deletes all alarm devices from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada 
    session.
    :type x_verkada_auth: str
    :param usr: The user ID of the authenticated user for a valid Verkada
    Command session.
    :type usr: str
    """
    threads = []

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr,
        "Content-Type": "application/json"
        "User": usr,
        "Content-Type": "application/json"
    }

    def delete_sensor(device_dict):
        """
        Deletes a generic wireless alarm sensor from Verkada Command.

        :param device_dict: A dictionary of all wireless devices that includes
        their ID and the device type.
        :type device_dict: dictionary
        """
        """
        Deletes a generic wireless alarm sensor from Verkada Command.

        :param device_dict: A dictionary of all wireless devices that includes
        their ID and the device type.
        :type device_dict: dictionary
        """
        for device in device_dict:
            data = {
            data = {
                "deviceId": device.get("deviceId"),
                "deviceType": device.get("deviceType"),
                "organizationId": org_id
                "deviceType": device.get("deviceType"),
                "organizationId": org_id
            }

            print(data)
            try:
                response = session.post(
                    ASENSORS_DECOM, headers=headers, json=data)
                response.raise_for_status()  # Raise an exception for HTTP errors

                log.debug(
                    f"Deleted wireless sensor: "
                    f"{device.get('deviceType')}"
                )

               # Handle exceptions
            except requests.exceptions.Timeout:
                log.error(f"{Fore.RED}Connection timed out.{Style.RESET_ALL}")

            except requests.exceptions.TooManyRedirects:
                log.error(
                    f"{Fore.RED}"
                    f"Too many redirects. Aborting..."
                    f"{Style.RESET_ALL}"
                )

            except requests.exceptions.HTTPError:
                log.error(
                    f"{Fore.RED}"
                    f"Wireless alarm sensor returned with a non-200"
                    f" code: {response.status_code}{Style.RESET_ALL}"
                )

            except requests.exceptions.ConnectionError:
                log.error(
                    f"{Fore.RED}"
                    f"Error connecting to the server."
                    f"{Style.RESET_ALL}"
                )

            except requests.exceptions.RequestException as e:
                log.error(f"{Fore.RED}Verkada API Error:{Style.RESET_ALL} {e}")

    def delete_keypads(device_ids):
        """
        Deletes a generic wireless alarm sensor from Verkada Command.

        :param device_dict: A dictionary of all wireless devices that includes
        their ID and the device type.
        :type device_dict: dict
        """
        processed_ids = set()
        for device_id in device_ids:
            if device_id not in processed_ids:
                data = {
                data = {
                    "deviceId": device_id,
                    "organizationId": org_id
                }

                try:
                    log.debug(f"Running for {device_id}")
                    response = session.post(
                        AKEYPADS_DECOM, headers=headers, json=data)
                    response.raise_for_status()  # Raise an exception for HTTP errors

                    processed_ids.add(device_id)
                    log.debug(f"Keypad deleted: {device_id}")

               # Handle exceptions
                except requests.exceptions.Timeout:
                    log.error(f"{Fore.RED}Connection timed out.{Style.RESET_ALL}")

                except requests.exceptions.TooManyRedirects:
                    log.error(
                        f"{Fore.RED}"
                        f"Too many redirects. Aborting..."
                        f"{Style.RESET_ALL}"
                    )

                except requests.exceptions.HTTPError:
                    if response.status_code == 400:
                        log.debug("Trying as keypad.")
                        response = session.post(
                        APANEL_DECOM,
                        headers=headers,
                        json=data
                        )
                        if response.status == 200:
                            log.debug(
                                f"{Fore.GREEN}"
                                f"Keypad deleted successfully"
                                )
                        else:
                            log.warning(
                                f"{Fore.RED}"
                                f"Could not delete {device_id}"
                                f"{Style.RESET_ALL}\nStatus code: "
                                f"{response.status_code}"
                            )
                        
                    else:
                        log.error(
                            f"{Fore.RED}"
                            f"Alarm keypad returned with a non-200"
                            f" code: {response.status_code}{Style.RESET_ALL}"
                        )

                except requests.exceptions.ConnectionError:
                    log.error(
                        f"{Fore.RED}"
                        f"Error connecting to the server."
                        f"{Style.RESET_ALL}"
                    )

                except requests.exceptions.RequestException as e:
                    log.error(f"{Fore.RED}Verkada API Error:{Style.RESET_ALL} {e}")

    def convert_to_dict(array, deviceType):
        """
        Converts an array to a dictionary that containes the attribute
        device type.

        :param array: The array to convert.
        :type array: list
        :param deviceType: The value to be used for the device type attribute.
        :type deviceType: str
        :return: Returns a dictionary containing the attribute device type.
        :rtype: dict
        """
        """
        Converts an array to a dictionary that containes the attribute
        device type.

        :param array: The array to convert.
        :type array: list
        :param deviceType: The value to be used for the device type attribute.
        :type deviceType: str
        :return: Returns a dictionary containing the attribute device type.
        :rtype: dict
        """
        device_dict = []

        if isinstance(array, str):
            array = [array]  # Force the input to be an array

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
        x_verkada_token, x_verkada_auth, usr, session, org_id)

    # Check if it is empty, if so, skip. If not, turn it into a dictionary.
    if dcs:
        door_thread = threading.Thread(target=delete_sensor, args=(
            convert_to_dict(dcs, "doorContactSensor"),))
        threads.append(door_thread)
    if gbs:
        glass_thread = threading.Thread(target=delete_sensor, args=(
            convert_to_dict(gbs, "glassBreakSensor"),))
        threads.append(glass_thread)
    if hub:
        keypad_thread = threading.Thread(target=delete_keypads, args=(hub,))
        threads.append(keypad_thread)
    if ms:
        motion_thread = threading.Thread(target=delete_sensor, args=(
            convert_to_dict(ms, "motionSensor"),))
        threads.append(motion_thread)
    if pb:
        panic_thread = threading.Thread(target=delete_sensor, args=(
            convert_to_dict(pb, "panicButton"),))
        threads.append(panic_thread)
    if ws:
        water_thread = threading.Thread(target=delete_sensor, args=(
            convert_to_dict(ws, "waterSensor"),))
        threads.append(water_thread)
    if wr:
        relay_thread = threading.Thread(target=delete_sensor, args=(
            convert_to_dict(wr, "wirelessRelay"),))
        threads.append(relay_thread)

    # Check if there are threads waiting to be ran.
    if threads:
        # Run the threads
        for thread in threads:
            thread.start()
        # Wait for them to finish
        for thread in threads:
            thread.join()

        log.info(f"{Fore.GREEN}Alarm sensors deleted.{Style.RESET_ALL}")

    else:
        log.warning("No alarm sensors were received.")


def deletePanels(x_verkada_token, x_verkada_auth, usr,
                 org_id=ORG_ID):
    """
    Deletes all acces control panels from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada 
    session.
    :type x_verkada_auth: str
    """
    exempt = [
        '1e4c5613-d9f0-4030-94b1-9daef6d0f84e',
        '3d3295e6-30da-44eb-bc05-bfa47249afbd',
        '43fa1fcd-17f0-4b95-9c24-ac8ff38131ed',
        '90c971bd-2a15-4305-bc8c-710374a3d089',
        'a41766d1-4cd7-4331-a7ed-c4e874a31147',
        'ff4731b6-ae7c-4194-934c-b6a3770d1f7b'
    ]
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting Access control panels.")
        panels = gatherDevices.list_AC(x_verkada_token, x_verkada_auth,
                                       usr, session, org_id)
        if panels:
            for panel in panels:
                if panel not in exempt:
                    log.debug(f"Running for access control panel: {panel}")

                    data = {
                        "deviceId": panel
                    }
                if panel not in exempt:
                    log.debug(f"Running for access control panel: {panel}")

                    data = {
                        "deviceId": panel
                    }

                    response = session.post(
                        ACCESS_DECOM, headers=headers, json=data)
                    response.raise_for_status()  # Raise an exception for HTTP errors
                    response = session.post(
                        ACCESS_DECOM, headers=headers, json=data)
                    response.raise_for_status()  # Raise an exception for HTTP errors

            log.debug("Access control panels deleted.")

        else:
            log.warning("No Access control panels were received.")

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"{Fore.RED}Connection timed out.{Style.RESET_ALL}")

    except requests.exceptions.TooManyRedirects:
        log.error(
            f"{Fore.RED}"
            f"Too many redirects. Aborting..."
            f"{Style.RESET_ALL}"
        )

    except requests.exceptions.HTTPError:
        log.error(
            f"Access control panels returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(
            f"{Fore.RED}"
            f"Error connecting to the server."
            f"{Style.RESET_ALL}"
        )

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


def deleteEnvironmental(x_verkada_token, x_verkada_auth, usr,
                        org_id=ORG_ID):
    """
    Deletes all environmental sensors from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada 
    session.
    :type x_verkada_auth: str
    """
    params = {
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
                                            usr, session, org_id)
        if sv_ids:
            for sensor in sv_ids:
                data = {
                    "deviceId": sensor
                }

                log.info(f"Running for environmental sensor {sensor}")

                response = session.post(
                    ENVIRONMENTAL_DECOM,
                    json=data,
                    headers=headers,
                    params=params
                )
                response.raise_for_status()  # Raise an exception for HTTP errors

            log.info(
                f"{Fore.GREEN}"
                f"Environmental sensors deleted."
                f"{Style.RESET_ALL}"
            )

        else:
            log.warning(
                f"{Fore.MAGENTA}"
                f"No environmental sensors were received."
                f"{Style.RESET_ALL}"
            )

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"{Fore.RED}Connection timed out.{Style.RESET_ALL}")

    except requests.exceptions.TooManyRedirects:
        log.error(
            f"{Fore.RED}"
            f"Too many redirects. Aborting..."
            f"{Style.RESET_ALL}"
        )

    except requests.exceptions.HTTPError:
        log.error(
            f"{Fore.RED}"
            f"Environmental sensor returned with a non-200 code: "
            f"{response.status_code}{Style.RESET_ALL}"
        )

    except requests.exceptions.ConnectionError:
        log.error(
            f"{Fore.RED}"
            f"Error connecting to the server."
            f"{Style.RESET_ALL}"
        )

    except requests.exceptions.RequestException as e:
        log.error(f"{Fore.RED}Verkada API Error:{Style.RESET_ALL} {e}")


if __name__ == '__main__':
    start_run_time = time.time()  # Start timing the script
    with requests.Session() as session:
        try:
            # Initialize the user session.
            csrf_token, user_token, user_id = login_and_get_tokens()
    start_run_time = time.time()  # Start timing the script
    with requests.Session() as session:
        try:
            # Initialize the user session.
            csrf_token, user_token, user_id = login_and_get_tokens()

            # Continue if the required information has been received
            if csrf_token and user_token and user_id:
                # Place each element in their own thread to speed up runtime
                camera_thread = threading.Thread(
                    target=deleteCameras, args=(
                        csrf_token, user_token, user_id,))

                alarm_thread = threading.Thread(target=deleteSensors, args=(
                    csrf_token, user_token, user_id, session,))

                ac_thread = threading.Thread(
                    target=deletePanels, args=(
                        csrf_token, user_token, user_id,))

                sv_thread = threading.Thread(
                    target=deleteEnvironmental, args=(
                        csrf_token, user_token, user_id,))

                # List all the threads to be ran
                threads = [camera_thread, alarm_thread, ac_thread, sv_thread]

                # Start the threads
                for thread in threads:
                    thread.start()

                # Join the threads as they finish
                for thread in threads:
                    thread.join()

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
        finally:
            if csrf_token and user_token:
                log.debug("Logging out.")
                logout(csrf_token, user_token)
            session.close()
            log.debug("Session closed.\nExiting...")
