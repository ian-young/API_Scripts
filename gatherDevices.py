# Author: Ian Young
# Purpose: Iterate through all archives that are visible to a user and delete
# them. This is ONLY to be used to keep a given org clean. Extreme caution is
# advised since the changes this script will make to the org cannot be undone
# once made.

# Import essential libraries
import threading
import requests
import logging
import time
from os import getenv
from dotenv import load_dotenv

load_dotenv()

# Set final, global credential variables
USERNAME = getenv("lab_username")
PASSWORD = getenv("lab_password")
ORG_ID = getenv("lab_id")

# Set final, global URLs
LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
LOGOUT_URL = "https://vprovision.command.verkada.com/user/logout"
CAMERA_URL = "https://api.verkada.com/cameras/v1/devices"
AUDIT_URL = "https://api.verkada.com/core/v1/audit_log"
AC_URL = "https://vcerberus.command.verkada.com/get_entities"
ALARM_URL = "https://alarms.command.verkada.com/device/get_all"
VX_URL = "https://vvx.command.verkada.com/device/list"
GC_URL = "https://vnet.command.verkada.com/devices/list"
SV_URL = "https://vsensor.command.verkada.com/devices/list"
BZ_URL = "https://vbroadcast.command.verkada.com/management/speaker/list"
# TODO: Find Desk Station endpoint
TD_URL = ""
# Filter 'sites' first. Each site is an object.
SITES = "https://vdoorman.command.verkada.com/user/valid_sites/org/"
# PRINTER_TABLETS = f"https://vdoorman.command.verkada.com/site/settings/v2/org\
# /{ORG_ID}/site/{site_id}"

# Set up the logger
log = logging.getLogger()
log.setLevel(logging.INFO)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

devices_serials = []
ARRAY_LOCK = threading.Lock()

##############################################################################
                        #   Thread Management   #
##############################################################################


class ResultThread(threading.Thread):
    """
    A subclass of threading's Thread. Creates a new thread where the return
    values are saved to be viewed for later. They may be accessed by typing
    the objectname.result
    """
    def __init__(self, target, *args, **kwargs):
        super().__init__(target=target, args=args, kwargs=kwargs)
        self._result = None

    def run(self):
        self._result = self._target(*self._args, **self._kwargs)

    @property
    def result(self):
        return self._result

# Define a helper function to create threads with arguments
def create_thread_with_args(target, args):
    """
    Allows the creation of a ResultThread and still pass arguments to the
    thread.

    :param target: The function that the thread will be running.
    :type target: function
    :param args: The arguments that will be passed through the function.
    :type args: Any
    :return: Returns a ResultThread
    :rtype: thread
    """
    return ResultThread(target=lambda: target(*args))


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
                            #   Requests   #
##############################################################################


def list_cameras(api_key, session):
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json'
    }

    camera_ids = []
    log.debug("Requesting camera data")

    try:
        response = session.get(CAMERA_URL, headers=headers)
        response.raise_for_status()
        log.debug("-------")
        log.debug("Camera data retrieved.")

        cameras = response.json()['cameras']

        # print("-------")
        # print("Cameras:")
        for camera in cameras:
            camera_ids.append(camera['camera_id'])
            # print(camera['camera_id'])

        return camera_ids

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Cameras returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


# TODO: Need to troubleshoot. Only giving parent sites.
def get_sites(x_verkada_token, x_verkada_auth, usr,
              org_id=ORG_ID):
    """
    Lists all Verkada Guest sites.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: An array of all Verkada sites.
    :rtype: list
    """
    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    url = SITES + org_id
    site_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting access control devices.")
        # print(url)
        response = session.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Access control JSON retrieved. Parsing and logging.")

        sites = response.json()['sites']

        # print("-------")
        # print("Sites:")
        for site in sites:
            log.debug(site['siteId'] + " " + site['siteName'])
            site_ids.append(site['siteId'])
            # print(site['siteId'])

        return site_ids

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Sites returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


def list_AC(x_verkada_token, x_verkada_auth, usr,
            org_id=ORG_ID):
    """
    Lists all access control devices.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: An array of door controller device IDs.
    :rtype: list
    """
    body = {
        "organizationId": org_id
    }

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    access_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting access control devices.")
        response = session.post(AC_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Access control JSON retrieved. Parsing and logging.")

        access_devices = response.json()['accessControllers']

        # print("-------")
        # print("Door controllers:")
        for controller in access_devices:
            access_ids.append(controller['deviceId'])

        return access_ids

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Access control returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None

    except KeyError:
        log.warning("No controllers found.")
        return None


def list_Alarms(x_verkada_token, x_verkada_auth, usr,
                org_id=ORG_ID):
    """
    Lists all alarm devices.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: Arrays of each wireless alarm sensor type device IDs.
    :rtype: lists
    """
    body = {
        "organizationId": org_id
    }

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    dcs_ids = []
    gbs_ids = []
    hub_ids = []
    ms_ids = []
    pb_ids = []
    ws_ids = []
    wr_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting alarm devices.")
        response = session.post(ALARM_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Alarm JSON retrieved. Parsing and logging.")

        alarm_devices = response.json()

        # print("-------")
        # print("Door contacts:")
        for dcs in alarm_devices['doorContactSensor']:
            dcs_ids.append(dcs['deviceId'])
            # print(dcs['deviceId'])
        # print("-------")
        # print("Glass break:")
        for gbs in alarm_devices['glassBreakSensor']:
            gbs_ids.append(gbs['deviceId'])
            # print(gbs['deviceId'])
        # print("-------")
        # print("Hub devices:")
        for hub in alarm_devices['hubDevice']:
            hub_ids.append(hub['deviceId'])
            # print(hub['deviceId'])
        # print("-------")
        # print("Keypads:")
        for keypad in alarm_devices['keypadHub']:
            hub_ids.append(keypad['deviceId'])
            # print(keypad['deviceId'])
        # print("-------")
        # print("Motion sensors:")
        for ms in alarm_devices['motionSensor']:
            ms_ids.append(ms['deviceId'])
            # print(ms['deviceId'])
        # print("-------")
        # print("Panic buttons:")
        for pb in alarm_devices['panicButton']:
            pb_ids.append(pb['deviceId'])
            # print(pb['deviceId'])
        # print("-------")
        # print("Water sensors:")
        for ws in alarm_devices['waterSensor']:
            ws_ids.append(ws['deviceId'])
            # print(ws['deviceId'])
        # print("-------")
        # print("Wireless Relays:")
        for wr in alarm_devices['wirelessRelay']:
            wr_ids.append(wr['deviceId'])
            # print(wr['deviceId'])

        return dcs_ids, gbs_ids, hub_ids, ms_ids, pb_ids, ws_ids, wr_ids

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Alarms returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


def list_Viewing_Stations(x_verkada_token, x_verkada_auth, usr,
                          org_id=ORG_ID):
    """
    Lists all viewing stations.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: An array of archived video station device IDs.
    :rtype: list
    """
    body = {
        "organizationId": org_id
    }

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    vx_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting viewing stations.")
        response = session.post(VX_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Viewing station JSON retrieved. Parsing and logging.")

        vx_devices = response.json()['viewingStations']

        # print("-------")
        # print("Viewing stations:")
        for vx in vx_devices:
            vx_ids.append(vx['viewingStationId'])
            # print(vx['viewingStationId'])

        return vx_ids

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Viewing stations returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


def list_Gateways(x_verkada_token, x_verkada_auth, usr,
                  org_id=ORG_ID):
    """
    Lists all cellular gateways.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: An array of gateway device IDs.
    :rtype: list
    """
    body = {
        "organizationId": org_id
    }

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    gc_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting cellular gateways.")
        response = session.post(GC_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Cellular gateways JSON retrieved. Parsing and logging.")

        gc_devices = response.json()

        # print("-------")
        # print("Gateways:")
        for gc in gc_devices:
            gc_ids.append(gc['device_id'])
            # print(gc['device_id'])

        return gc_ids

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        if response.status_code == 404:
            log.warning("No gateways were found in the org.")
        else:
            log.error(
                f"Gateways returned with a non-200 code: "
                f"{response.status_code}"
            )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


def list_Sensors(x_verkada_token, x_verkada_auth, usr,
                 org_id=ORG_ID):
    """
    Lists all environmental sensors.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: An array of environmental sensor device IDs.
    :rtype: list
    """
    body = {
        "organizationId": org_id
    }

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    sv_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting environmental sensors.")
        response = session.post(SV_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Environmental sensors JSON retrieved. Parsing and logging.")

        sv_devices = response.json()['sensorDevice']

        # print("-------")
        # print("Environmental sensors:")
        for sv in sv_devices:
            sv_ids.append(sv['deviceId'])
            # print(sv['deviceId'])

        return sv_ids

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Sensors returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


def list_Horns(x_verkada_token, x_verkada_auth, usr,
               org_id=ORG_ID):
    """
    Lists all BZ horn speakers.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: An array of BZ11 device IDs.
    :rtype: list
    """
    body = {
        "organizationId": org_id
    }

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr
    }

    bz_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting horn speakers.")
        response = session.post(BZ_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Horn speakers JSON retrieved. Parsing and logging.")

        bz_devices = response.json()['garfunkel']

        # print("-------")
        # print("Horn speakers (BZ11):")
        for bz in bz_devices:
            bz_ids.append(bz['deviceId'])
            # print(bz['deviceId'])

        return bz_ids

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Horns returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None

    except KeyError:
        log.warning("No BZ11s found in org.")
        return None


def list_DeskStaions(x_verkada_token, x_verkada_auth, usr,
                     org_id=ORG_ID):
    """
    Lists all intercom-related devices (TD and desk station).

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: An array of archived video export IDs.
    :rtype: list
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
        log.debug("Requesting intercom-related devices.")
        response = session.post(TD_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Intercom devices JSON retrieved. Parsing and logging.")

        #! Will need to adjust this as the right endpoint is found.
        td_devices = response.json()['deskStation']

        # print("-------")
        # print("Intercom-related devices:")
        for td in td_devices:
            # print(td['deviceId'])
            with ARRAY_LOCK:
                devices_serials.append(td['deviceId'])

        return td_devices

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


##############################################################################
                                #   Main   #
##############################################################################


# Check if the script is being imported or ran directly
if __name__ == "__main__":

    with requests.Session() as session:
        start_run_time = time.time()  # Start timing the script
        try:
            # Initialize the user session.
            csrf_token, user_token, user_id = login_and_get_tokens()

            # Continue if the required information has been received
            if csrf_token and user_token and user_id:
                # Define the threads with arguments
                c_thread = create_thread_with_args(list_cameras, [])
                ac_thread = create_thread_with_args(
                    list_AC, [csrf_token, user_token, user_id, ORG_ID])
                br_thread = create_thread_with_args(
                    list_Alarms, [csrf_token, user_token, user_id, ORG_ID])
                vx_thread = create_thread_with_args(
                    list_Viewing_Stations, [csrf_token, user_token, user_id, ORG_ID])
                gc_thread = create_thread_with_args(
                    list_Gateways, [csrf_token, user_token, user_id, ORG_ID])
                sv_thread = create_thread_with_args(
                    list_Sensors, [csrf_token, user_token, user_id, ORG_ID])
                bz_thread = create_thread_with_args(
                    list_Horns, [csrf_token, user_token, user_id, ORG_ID])

                threads = [c_thread, ac_thread, br_thread, vx_thread,
                           gc_thread, sv_thread, bz_thread]

                for thread in threads:
                    thread.start()

                for thread in threads:
                    thread.join()

                #--for thread in threads:
                #--    print(thread.result)
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
            log.warning(f"\nKeyboard interrupt detected. Logging out & aborting...")

        finally:
            if csrf_token and user_token:
                log.debug("Logging out.")
                logout(csrf_token, user_token)
            session.close()
            log.debug("Session closed.\nExiting...")
