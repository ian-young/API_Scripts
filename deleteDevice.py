# Author: Ian Young
# Purpose: Reset a Verkada Command organization for use at VCE. An API key and
# valid user credentials are needed to run this script. Please use EXTREME
# caution when running because this will delete all devices from an org
# without any additional warnings.
import colorama
import gatherDevices
import logging
import requests
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

# Set final, global credential variables
API_KEY = getenv()
USERNAME = getenv()
PASSWORD = getenv()
ORG_ID = getenv()


# Root API URL
ROOT = "https://api.command.verkada.com/vinter/v1/user/async"
SHARD = "?sharding=true"

# Set final, global URLs
# * POST
ACCESS_DECOM = "https://vcerberus.command.verkada.com/access_device/decommission"
AKEYPADS_DECOM = "https://alarms.command.verkada.com/device/keypad_hub/decommission"
APANEL_DECOM = "https://alarms.command.verkada.com/device/hub/decommission"
ASENSORS_DECOM = "https://alarms.command.verkada.com/device/sensor/delete"
CAMERA_DECOM = "https://vprovision.command.verkada.com/camera/decommission"
ENVIRONMENTAL_DECOM = "https://vsensor.command.verkada.com/devices/decommission"
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"
# * DELETE
DESK_DECOM = f"{ROOT}/organization/{ORG_ID}/device/"
GUEST_IPADS_DECOM = f"https://vdoorman.command.verkada.com/device/org/\
{ORG_ID}/site/"
GUEST_PRINTER_DECOM = f"https://vdoorman.command.verkada.com/printer/org/\
{ORG_ID}/site/"
# * PUT
ACCESS_LEVEL_DECOM = f"https://vcerberus.command.verkada.com/organizations/\
{ORG_ID}/schedules"


##############################################################################
                                #  Misc  #
##############################################################################


class RateLimiter:
    def __init__(self, rate_limit, max_events_per_sec=10, pacing=1):
        """
        Initilization of the rate limiter.

        :param rate_limit: The value of how many threads may be made each sec.
        :type rate_limit: int
        :param max_events_per_sec: Maximum events allowed per second.
        :type: int, optional
        :param pacing: Sets the interval of the clock in seconds.
        :type pacing: int, optional
        :return: None
        :rtype: None
        """
        self.rate_limit = rate_limit
        self.lock = threading.Lock()  # Local lock to prevent race conditions
        self.max_events_per_sec = max_events_per_sec
        self.pacing = pacing

    def acquire(self):
        """
        States whether or not the program may create new threads or not.

        :return: Boolean value stating whether new threads may be made or not.
        :rtype: bool
        """
        with self.lock:
            current_time = time.time()  # Define current time

            if not hasattr(self, 'start_time'):
                # Check if attribue 'start_time' exists, if not, make it.
                self.start_time = current_time
                self.event_count = self.pacing
                return True

            # How much time has passed since starting
            elapsed_time = current_time - self.start_time

            # Check if it's been less than 1sec and less than 10 events have
            # been made.
            if elapsed_time < self.pacing / self.rate_limit \
                    and self.event_count < self.max_events_per_sec:
                self.event_count += 1
                return True

            # Check if it is the first wave of events
            elif elapsed_time >= self.pacing / self.rate_limit:
                self.start_time = current_time
                self.event_count = 2
                return True

            else:
                # Calculate the time left before next wave
                remaining_time = self.pacing - \
                    (current_time - self.start_time)
                time.sleep(remaining_time)  # Wait before next wave
                return True


def run_thread_with_rate_limit(threads, rate_limit=2):
    """
    Run a thread with rate limiting.

    :param threads: A list of threads that need to be clocked.
    :type threads: list
    :param rate_limit: The value of how many threads may be made each sec.
    :type rate_limit: int
    :return: The thread that was created and ran.
    :rtype: thread
    """
    limiter = RateLimiter(
        rate_limit=rate_limit,
        max_events_per_sec=rate_limit
    )

    def run_thread(thread):
        with threading.Lock():
            limiter.acquire()

            log.debug(
                f"{Fore.LIGHTBLACK_EX}"
                f"Starting thread "
                f"{Fore.LIGHTYELLOW_EX}{thread.name}{Style.RESET_ALL} "
                f"{Fore.LIGHTBLACK_EX}"
                f"at time {datetime.now().strftime('%H:%M:%S')}"
                f"{Style.RESET_ALL}"
            )
            thread.start()

    for thread in threads:
        run_thread(thread)

    for thread in threads:
        thread.join()


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
##############################################################################


##############################################################################
                                #   Requests   #
##############################################################################


def deleteCameras(x_verkada_token, usr, org_id=ORG_ID):
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
        "x-verkada-organization-id": org_id,
        "x-verkada-token": x_verkada_token,
        "x-verkada-user-id": usr
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting cameras.")
        cameras = gatherDevices.list_Cameras(API_KEY, session)
        if cameras:
            for camera in cameras:
                body = {
                    "cameraId": camera
                }
                response = session.post(
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
            f"{Fore.RED}"
            f"Delete camera returned with a non-200 code: "
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
    }

    def delete_sensor(device_dict):
        """
        Deletes a generic wireless alarm sensor from Verkada Command.

        :param device_dict: A dictionary of all wireless devices that includes
        their ID and the device type.
        :type device_dict: dictionary
        """
        for device in device_dict:
            data = {
                "deviceId": device.get("deviceId"),
                "deviceType": device.get("deviceType"),
                "organizationId": org_id
            }

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
                    "deviceId": device_id,
                    "organizationId": org_id
                }

                try:
                    log.debug(f"Running for {device_id}")
                    response = session.post(
                        APANEL_DECOM, headers=headers, json=data)
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
        log.warning(
            f"{Fore.MAGENTA}"
            f"No alarm sensors were received."
            f"{Style.RESET_ALL}"
        )


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

                    response = session.post(
                        ACCESS_DECOM, headers=headers, json=data)
                    response.raise_for_status()  # Raise an exception for HTTP errors

            log.info(
                f"{Fore.GREEN}"
                f"Access control panels deleted."
                f"{Style.RESET_ALL}")

        else:
            log.warning(
                f"{Fore.MAGENTA}"
                f"No Access control panels were received."
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
        if response.status_code == 400:
            log.debug(f"{Fore.MAGENTA}"
                      f"Trying {panel} as intercom."
                      f"{Style.RESET_ALL}"
            )
            deleteIntercom(x_verkada_token, usr, panel)
        else:
            log.error(
                f"{Fore.RED}"
                f"Access control panel returned with a non-200 code: "
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


def deleteIntercom(x_verkada_token, usr, device_id, org_id=ORG_ID):
    """
    Deletes all Intercoms from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada 
    session.
    :type x_verkada_auth: str
    """
    headers = {
        "x-verkada-organization-id": org_id,
        "x-verkada-token": x_verkada_token,
        "x-verkada-user-id": usr
    }

    try:
        url = DESK_DECOM + device_id + SHARD

        log.debug(f"Running for intercom: {device_id}")

        response = session.delete(
            url,
            headers=headers
        )
        response.raise_for_status()  # Raise for HTTP errors

        log.info(f"{Fore.GREEN}Intercom deleted.{Style.RESET_ALL}")

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
            f"Intercom returned with a non-200 code: "
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


def deleteGuest(x_verkada_token, x_verkada_auth, usr,
                org_id=ORG_ID):
    """
    Deletes all Guest devices from a Verkada organization.

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
        # Request the JSON library for Sites
        log.debug("Initiating site request.")
        sites = gatherDevices.get_Sites(
            x_verkada_token, x_verkada_auth, usr, session, org_id)

        # Request the JSON library for Guest
        log.debug("Initiating Guest requests.")
        ipad_ids, printer_ids = gatherDevices.list_Guest(
            x_verkada_token, x_verkada_auth, usr, session, org_id, sites)

        for site in sites:
            ipad_present = True
            printer_present = True
            
            if ipad_ids:
                for ipad in ipad_ids:
                    url = f"{GUEST_IPADS_DECOM}{site}?deviceId={ipad}"

                    log.debug(f"Running for iPad: {ipad}")

                    response = session.delete(
                        url,
                        headers=headers,
                        params=params
                    )
                    response.raise_for_status()  # Raise for HTTP errors

                log.info(
                    f"{Fore.GREEN}"
                    f"iPads deleted for site {site}"
                    f"{Style.RESET_ALL}"
                )

            else:
                ipad_present = False
                log.debug("No iPads present.")

            if printer_ids:
                for printer in printer_ids:
                    url = f"{GUEST_PRINTER_DECOM}{site}?printerId={printer}"

                    log.debug(f"Running for printer: {printer}")

                    response = session.delete(
                        url,
                        headers=headers,
                        params=params
                    )
                    response.raise_for_status()  # Raise for HTTP errors

                log.info(
                    f"{Fore.GREEN}"
                    f"Printers deleted for site {site}"
                    f"{Style.RESET_ALL}"
                )

            else:
                printer_present = False
                log.debug("No printers present.")

            if not ipad_present and not printer_present:
                log.warning(
                    f"{Fore.MAGENTA}"
                    f"No Guest devices were received for site {site}."
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
            f"Guest returned with a non-200 code: "
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


def deleteACLs(x_verkada_token, usr, org_id=ORG_ID):
    """
    Deletes all access control levels from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada 
    session.
    :type x_verkada_auth: str
    """
    def find_schedule_by_id(schedule_id, schedules):
        for schedule in schedules:
            if schedule["scheduleId"] == schedule_id:
                return schedule
        return None

    headers = {
        "x-verkada-organization-id": org_id,
        "x-verkada-token": x_verkada_token,
        "x-verkada-user-id": usr
    }

    try:
        # Request the JSON archive library
        log.debug("Initiating request for access control levels.")
        acls, acl_ids = gatherDevices.list_ACLs(x_verkada_token, usr, session,
                                                org_id)
        
        if acls and acl_ids:
            for acl in acl_ids:
                schedule = find_schedule_by_id(acl, acls)
                log.info(f"Running for access control level {acl}")
                schedule['deleted'] = True
                data = {
                    'sitesEnabled': True,
                    'schedules': [schedule]
                }

                response = session.put(
                    ACCESS_LEVEL_DECOM,
                    json=data,
                    headers=headers
                )
                response.raise_for_status()  # Raise an exception for HTTP errors

            log.info(
                f"{Fore.GREEN}"
                f"Access control levels deleted."
                f"{Style.RESET_ALL}"
            )

        else:
            log.warning(
                f"{Fore.MAGENTA}"
                f"No access control levels were received."
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
            f"Access control levels returned with a non-200 code: "
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


def deleteDeskStation(x_verkada_token, usr, org_id=ORG_ID):
    """
    Deletes all Guest devices from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada 
    session.
    :type x_verkada_auth: str
    """
    headers = {
        "x-verkada-organization-id": org_id,
        "x-verkada-token": x_verkada_token,
        "x-verkada-user-id": usr
    }

    try:
        # Request the JSON library for Desk Station
        log.debug("Initiating Desk Station requests.")
        ds_ids = gatherDevices.list_Desk_Stations(
            x_verkada_token, usr, session, org_id)

        if ds_ids:
            for desk_station in ds_ids:
                url = DESK_DECOM + desk_station + SHARD

                log.debug(
                    f"{Fore.GREEN}"
                    f"Running for Desk Station: {desk_station}"
                    f"{Style.RESET_ALL}"
                )

                response = session.delete(
                    url,
                    headers=headers
                )
                response.raise_for_status()  # Raise for HTTP errors

                log.info(
                    f"{Fore.GREEN}"
                    f"Desk Stations deleted."
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
            f"Desk station returned with a non-200 code: "
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


##############################################################################
                                #   Main   #
##############################################################################


if __name__ == '__main__':
    start_run_time = time.time()  # Start timing the script
    with requests.Session() as session:
        try:
            # Initialize the user session.
            csrf_token, user_token, user_id = login_and_get_tokens()

            # Continue if the required information has been received
            if csrf_token and user_token and user_id:
                # Place each element in their own thread to speed up runtime
                camera_thread = threading.Thread(
                    target=deleteCameras, 
                    args=(csrf_token, user_token,))

                alarm_thread = threading.Thread(
                    target=deleteSensors, 
                    args=(csrf_token, user_token, user_id, session,))

                ac_thread = threading.Thread(
                    target=deletePanels, 
                    args=(csrf_token, user_token, user_id,))

                sv_thread = threading.Thread(
                    target=deleteEnvironmental, 
                    args=(csrf_token, user_token, user_id,))

                guest_thread = threading.Thread(
                    target=deleteGuest, 
                    args=(csrf_token, user_token, user_id,))

                acl_thread = threading.Thread(
                    target=deleteACLs, 
                    args=(csrf_token, user_id,))

                desk_thread = threading.Thread(
                    target=deleteDeskStation, 
                    args=(csrf_token, user_token, user_id,))

                # # List all the threads to be ran
                threads = [camera_thread, alarm_thread, ac_thread, sv_thread,
                           guest_thread, acl_thread, desk_thread]

                # Start the clocked threads
                run_thread_with_rate_limit(threads)

            # Handles when the required credentials were not received
            else:
                log.critical(
                    f"{Fore.MAGENTA}"
                    f"No credentials were provided during "
                    f"the authentication process or audit log "
                    f"could not be retrieved."
                    f"{Style.RESET_ALL}"
                )

            # Calculate the time take to run and post it to the log
            elapsed_time = time.time() - start_run_time
            log.info("-------")
            log.info(
                f"Total time to complete "
                f"{Fore.CYAN}{elapsed_time:.2f}s{Style.RESET_ALL}"
            )

        # Gracefully handle an interrupt
        except KeyboardInterrupt:
            print(
                f"{Fore.RED}\nKeyboard interrupt detected. "
                f"Logging out & aborting...{Style.RESET_ALL}"
            )

        finally:
            if csrf_token and user_token:
                log.debug("Logging out.")
                logout(csrf_token, user_token)
            session.close()
            log.debug("Session closed.\nExiting...")
