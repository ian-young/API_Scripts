# Author: Ian Young
# Purpose: Iterate through all archives that are visible to a user and delete
# them. This is ONLY to be used to keep a given org clean. Extreme caution is
# advised since the changes this script will make to the org cannot be undone
# once made.

# Import essential libraries
import json
import threading
import requests
import logging
import time
from os import getenv
from dotenv import load_dotenv
from tinydb import TinyDB, Query

load_dotenv()

Device = Query()
db_path = 'devices.json'
db = TinyDB(db_path)

# Set final, global credential variables
USERNAME = getenv("lab_username")
PASSWORD = getenv("lab_password")
ORG_ID = getenv("LAB_ID")

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
# TODO: Find TD endpoint
TD_URL = ""

# Set up the logger
log = logging.getLogger()
log.setLevel(logging.DEBUG)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s"
)

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

devices_serials = []
ARRAY_LOCK = threading.Lock()


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
            f"Login returned with a non-200 code: "
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


def get_audit_log(start_time, end_time):
    headers = {
        'x-api-key': getenv("LAB_KEY"),
        'Content-Type': 'application/json'
    }
    url = f"{AUDIT_URL}?start_time={start_time}&end_time={end_time}"
    log.debug("Requesting logs.")

    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
        log.debug("Logs retrieved.")

        return response.json()['audit_logs']

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
        log.error(
            f"Audit logs returned with a non-200 code: "
            f"{response.status_code}"
        )
        return None

    except requests.exceptions.ConnectionError:
        log.error(f"Error connecting to the server.")
        return None

    except requests.exceptions.RequestException as e:
        log.error(f"Verkada API Error: {e}")
        return None


def list_cameras():
    headers = {
        'x-api-key': getenv("LAB_KEY"),
        'Content-Type': 'application/json'
    }
    log.debug("Requesting camera data")

    try:
        response = session.get(CAMERA_URL, headers=headers)
        response.raise_for_status()
        log.debug("Camera data retrieved.")

        cameras = response.json()['cameras']

        print("-------")
        print("Cameras")
        for camera in cameras:
            print(camera['serial'])
            with ARRAY_LOCK:
                devices_serials.append(camera['serial'])
                build_db(camera['serial'], 'camera')

        return cameras

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
        log.debug("Requesting access control devices.")
        response = session.post(AC_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Access control JSON retrieved. Parsing and logging.")

        access_devices = response.json()['accessControllers']

        print("-------")
        print("Door controllers:")
        for controller in access_devices:
            print(controller['serialNumber'])
            with ARRAY_LOCK:
                devices_serials.append(controller['serialNumber'])
                build_db(controller['serialNumber'], 'controllers')

        return access_devices

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
        log.debug("Requesting alarm devices.")
        response = session.post(ALARM_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Alarm JSON retrieved. Parsing and logging.")

        alarm_devices = response.json()

        print("-------")
        print("Door contacts:")
        for dcs in alarm_devices['doorContactSensor']:
            print(dcs['serialNumber'])
            with ARRAY_LOCK:
                devices_serials.append(dcs['serialNumber'])
                build_db(dcs['serialNumber'], 'door_contact')
        print("-------")
        print("Glass break:")
        for gbs in alarm_devices['glassBreakSensor']:
            print(gbs['serialNumber'])
            with ARRAY_LOCK:
                devices_serials.append(gbs['serialNumber'])
                build_db(gbs['serialNumber'], 'glass_break')
        print("-------")
        print("Hub devices:")
        for hub in alarm_devices['hubDevice']:
            print(hub['claimedSerialNumber'])
            with ARRAY_LOCK:
                devices_serials.append(hub['claimedSerialNumber'])
                build_db(hub['claimedSerialNumber'], 'hub_device')
        print("-------")
        print("Keypads:")
        for keypad in alarm_devices['keypadHub']:
            print(keypad['claimedSerialNumber'])
            with ARRAY_LOCK:
                devices_serials.append(keypad['claimedSerialNumber'])
                build_db(keypad['claimedSerialNumber'], 'keypad')
        print("-------")
        print("Motion sensors:")
        for ms in alarm_devices['motionSensor']:
            print(ms['serialNumber'])
            with ARRAY_LOCK:
                devices_serials.append(ms['serialNumber'])
                build_db(ms['serialNumber'], 'motion_sensor')
        print("-------")
        print("Panic buttons:")
        for pb in alarm_devices['panicButton']:
            print(pb['serialNumber'])
            with ARRAY_LOCK:
                devices_serials.append(pb['serialNumber'])
                build_db(pb['serialNumber'], 'panic_button')
        print("-------")
        print("Water sensors:")
        for ws in alarm_devices['waterSensor']:
            print(ws['serialNumber'])
            with ARRAY_LOCK:
                devices_serials.append(ws['serialNumber'])
                build_db(ws['serialNumber'], 'water_Sensor')
        print("-------")
        print("Wireless Relays:")
        for wr in alarm_devices['wirelessRelay']:
            print(wr['serialNumber'])
            with ARRAY_LOCK:
                devices_serials.append(wr['serialNumber'])
                build_db(wr['serialNumber'], 'wireless_relay')

        return alarm_devices

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
        log.debug("Requesting viewing stations.")
        response = session.post(VX_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Viewing station JSON retrieved. Parsing and logging.")

        vx_devices = response.json()['viewingStations']

        print("-------")
        print("Viewing stations:")
        for vx in vx_devices:
            print(vx['claimedSerialNumber'])
            with ARRAY_LOCK:
                devices_serials.append(vx['claimedSerialNumber'])
                build_db(vx['claimedSerialNumber'], 'viewing_station')

        return vx_devices

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
        log.debug("Requesting cellular gateways.")
        response = session.post(GC_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Cellular gateways JSON retrieved. Parsing and logging.")

        gc_devices = response.json()

        print("-------")
        print("Gateways:")
        for gc in gc_devices:
            print(gc['claimed_serial_number'])
            with ARRAY_LOCK:
                devices_serials.append(gc['claimed_serial_number'])
                build_db(gc['claimed_serial_number'], 'gateway')

        return gc_devices

    # Handle exceptions
    except requests.exceptions.Timeout:
        log.error(f"Connection timed out.")
        return None

    except requests.exceptions.TooManyRedirects:
        log.error(f"Too many redirects.\nAborting...")
        return None

    except requests.exceptions.HTTPError:
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
        log.debug("Requesting environmental sensors.")
        response = session.post(SV_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Environmental sensors JSON retrieved. Parsing and logging.")

        sv_devices = response.json()['sensorDevice']

        print("-------")
        print("Environmental sensors:")
        for sv in sv_devices:
            print(sv['claimedSerialNumber'])
            with ARRAY_LOCK:
                devices_serials.append(sv['claimedSerialNumber'])
                build_db(sv['claimedSerialNumber'],
                         'environmental_sensor')

        return sv_devices

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
        log.debug("Requesting horn speakers.")
        response = session.post(BZ_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Horn speakers JSON retrieved. Parsing and logging.")

        bz_devices = response.json()['garfunkel']

        print("-------")
        print("Horn speakers (BZ11):")
        for bz in bz_devices:
            print(bz['serialNumber'])
            with ARRAY_LOCK:
                devices_serials.append(bz['serialNumber'])
                build_db(bz['serialNumber'], 'horn_speaker')

        return bz_devices

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


def list_Intercoms(x_verkada_token, x_verkada_auth, usr,
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

        print("-------")
        print("Intercom-related devices:")
        for td in td_devices:
            print(td['claimed_serial_number'])
            with ARRAY_LOCK:
                devices_serials.append(td['claimed_serial_number'])
                build_db(td['claimed_serial_number'], 'Desk Station')

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
                        #   Database   #
##############################################################################


def build_db(serial, type):
    log.debug("Adding table")
    device = {'serial': serial, 'product_line': type,
              'time_removed': '', 'who_removed': ''}
    existing_deivce = db.get(Device.serial == str(serial))

    if existing_deivce:
        log.debug("Found existing device.")
        db.update(device, Device.serial == str(serial))
    else:
        db.insert(device)
    log.debug("Device is currently in the table.")


def get_devices_removed_from_org(serials):
    """
    Checks against the table created by TinyDB to see which cameras have been 
    removed since the last time the script was ran.
    """

    log.info("--------------------")  # Aesthetic dividing line
    log.info("Serials Currently in Org")
    log.info(serials)

    stored_devices = db.search(Device.serial.exists())
    stored_serials = [device['serial'] for device in stored_devices]

    log.info("--------------------")  # Aesthetic dividing line
    log.info("Stored Serials")
    log.info(stored_serials)
    devices_not_in_sweep = db.search(
        ~Device.serial.one_of(serials))

    log.info("--------------------")  # Aesthetic dividing line
    log.info("Devices not in sweep")
    log.info(devices_not_in_sweep)

    for camera in devices_not_in_sweep:
        if camera['time_removed'] == "":
            camera['time_removed'] = int(time.time())
            db.update(camera,
                      Device.serial == str(camera['serial']))
            log.debug("--------------------")  # Aesthetic dividing line
            log.debug(json.dumps(camera, indent=2))

    return devices_not_in_sweep


def get_device_removed_user(serial, audit_log):
    """
    Will retrieve the user who removed a device from a Verkada Command
    orginazation.

    :param serial: The serial number of the Verkada device that was removed.
    :type serial: str
    :param audit_log: The audit log of actions taken in Verkada Command.
    :type audit_log: dict
    :return: Will return the user who removed a device from Verkada Command.
    :rtype: str
    """
    def is_correct_event(device_id):
        """
        Checks if the found event matches the device serial number in the
        audit log.

        :param device_id: The ID of a Verkada Camera.
        :type device_id: str
        :return: The email of the user that removed the Verkada Camera.
        :rtype: str
        """
        device_results = db.search(
            Device.camera_id == device_id)

        if len(device_results) > 0:
            device_details = device_results[0]
        else:
            return None

        log.debug(device_details)
        if device_details['serial'] == serial:
            user_email = event['user_email']
            return user_email
        else:
            return None
    log.info("--------------------")  # Aesthetic dividing line
    log.info(f"Finding who removed {serial}")

    devices_uninstalled = list(filter(
        lambda log: log['event_name'] == 'Devices Uninstalled',
        audit_log))

    for event in devices_uninstalled:
        event_devices = event['devices']
        if len(event_devices) < 1:
            return None
        for device in event_devices:
            correct_event = is_correct_event(str(device["device_id"]))

            if correct_event:
                log.info("Correct audit event:")
                log.info(correct_event)
                return correct_event


##############################################################################
                                #   Main   #
##############################################################################


# Check if the script is being imported or ran directly
if __name__ == "__main__":
    time_frame = 3600

    with requests.Session() as session:
        start_run_time = time.time()  # Start timing the script
        try:
            # Initialize the user session.
            csrf_token, user_token, user_id = login_and_get_tokens()
            timestamp = int(time.time())
            # Starting time frame is an hour ago because the script runs hourly
            start_time = timestamp - time_frame
            # If the device was removed within the past hour, make sure the function
            # doesn't try to search for a log in the future.
            end_time = timestamp + time_frame if timestamp + time_frame < \
                int(time.time()) else int(time.time())
            audit_log = get_audit_log(start_time, end_time)

            # Continue if the required information has been received
            if csrf_token and user_token and user_id and audit_log:

                log.debug("Retrieving cameras.")
                c_thread = threading.Thread(target=list_cameras)
                log.debug("Cameras retrieved")

                log.debug("Retrieving Access controllers.")
                ac_thread = threading.Thread(
                    target=list_AC,
                    args=(csrf_token, user_token, user_id, ORG_ID)
                )
                log.debug(f"Controllers retrieved.")

                log.debug("Retrieving Alarm devices.")
                br_thread = threading.Thread(
                    target=list_Alarms,
                    args=(csrf_token, user_token, user_id, ORG_ID)
                )
                log.debug(f"Alarm devices retrieved.")

                log.debug("Retrieving viewing stations.")
                vx_thread = threading.Thread(
                    target=list_Viewing_Stations,
                    args=(csrf_token, user_token, user_id, ORG_ID)
                )
                log.debug(f"Viewing stations retrieved.")

                log.debug("Retrieving cellular gateways.")
                gc_thread = threading.Thread(
                    target=list_Gateways,
                    args=(csrf_token, user_token, user_id, ORG_ID)
                )
                log.debug(f"Cellular gateways retrieved.")

                log.debug("Retrieving environmental sensors.")
                sv_thread = threading.Thread(
                    target=list_Sensors,
                    args=(csrf_token, user_token, user_id, ORG_ID)
                )
                log.debug(f"Environmental sensors retrieved.")

                log.debug("Retrieving horn speakers.")
                bz_thread = threading.Thread(
                    target=list_Horns,
                    args=(csrf_token, user_token, user_id, ORG_ID)
                )
                log.debug(f"Horn speakers retrieved.")

                #! Need to fix
                # log.debug("Retrieving intercom devices.")
                # td_thread = threading.Thread(
                #     target=list_Gateways,
                #     args=(csrf_token, user_token, user_id, ORG_ID)
                # )
                # log.debug(f"intercom devices retrieved.")

                threads = [c_thread, ac_thread, br_thread, vx_thread, 
                           gc_thread, sv_thread, bz_thread]

                # for thread in threads:
                #     thread.start()

                # for thread in threads:
                #     thread.join()

                ac_thread.start()
                ac_thread.join()

            # Handles when the required credentials were not received
            else:
                log.critical(
                    f"No credentials were provided during "
                    f"the authentication process or audit log "
                    f"could not be retrieved."
                )

            # Calculate the time take to run and post it to the log

            if audit_log is not None:
                log.info("--------------------")  # Aesthetic dividing line
                log.info("Got Audit log")
                removed_devices = get_devices_removed_from_org(devices_serials)
                for device in removed_devices:
                    user = get_device_removed_user(device['serial'],
                                                   audit_log)
                    if user is not None:
                        # Aesthetic dividing line
                        log.info("--------------------")
                        log.info(f"{user} deleted {device['serial']}")
                        device['time_removed'] = int(time.time())
                        device['who_removed'] = user
                        db.update(device,
                                  Device.serial == str(device['serial']))
                        print("Reminder to add device.")
                    else:
                        # Aesthetic dividing line
                        log.info("--------------------")
                        log.info(
                            f"No user found for deleted {device['serial']}")
                        print("Error email sent.")

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
