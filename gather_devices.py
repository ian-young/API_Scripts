"""
Author: Ian Young
Purpose: Will return all devices in a Verkada Command organization.
This is to be imported as a module and not ran directly.
"""
# Import essential libraries
import logging
import threading
import time
from os import getenv

import requests
from dotenv import load_dotenv

import custom_exceptions

load_dotenv()  # Load credentials file

# Set final, global credential variables
API_KEY = getenv("")
USERNAME = getenv("")
PASSWORD = getenv("")
ORG_ID = getenv("")

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
DESK_URL = f"https://api.command.verkada.com/vinter/v1/user/organization/\
{ORG_ID}/device"
IPAD_URL = f"https://vdoorman.command.verkada.com/site/settings/v2/org/\
{ORG_ID}/site/"
SITES = "https://vdoorman.command.verkada.com/user/valid_sites/org/"
ACCESS_LEVELS = f"https://vcerberus.command.verkada.com/organizations/\
{ORG_ID}/schedules"

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
        """
        Passes back the return value of the function ran.
        """
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


def login_and_get_tokens(login_session, username=USERNAME, password=PASSWORD, org_id=ORG_ID):
    """
    Initiates a Command session with the given user credentials and Verkada
    organization ID.

    :param login_session: The user session to use when making API calls.
    :type login_session: requests.Session
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
        response = login_session.post(LOGIN_URL, json=login_data)
        response.raise_for_status()
        log.debug("Session opened.")

        # Extract relevant information from the JSON response
        log.debug("Parsing JSON response.")
        json_response = response.json()
        session_token = json_response.get("csrfToken")
        session_user_token = json_response.get("userToken")
        session_user_id = json_response.get("userId")
        log.debug("Response parsed. Returning values.")

        return session_token, session_user_token, session_user_id

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e,
            response,
            "Login"
        )


def logout(logout_session, x_verkada_token, x_verkada_auth, org_id=ORG_ID):
    """
    Logs the Python script out of Command to prevent orphaned sessions.

    :param logout_session: The user session to use when making API calls.
    :type logout_session: requests.Session
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
        response = logout_session.post(LOGOUT_URL, headers=headers, json=body)
        response.raise_for_status()

        log.info("Logging out.")

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e,
            response,
            "Logout"
        )

    except KeyboardInterrupt:
        log.warning("Keyboard interrupt detected. Exiting...")

    finally:
        logout_session.close()


##############################################################################
                            #   Requests   #
##############################################################################


def list_cameras(api_key, camera_session):
    """
    Will list all cameras inside of a Verkada organization.

    :param api_key: The API key generated from the organization to target.
    :type api_key: str
    :param camera_session: The request session to use to make the call with.
    :type camera_session: object
    :return: Returns a list of all camera device IDs found inside of a Verkada
    organization.
    :rtype: list
    """
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json'
    }

    camera_ids = []
    log.debug("Requesting camera data")

    try:
        response = camera_session.get(CAMERA_URL, headers=headers)
        response.raise_for_status()
        log.debug("-------")
        log.debug("Camera data retrieved.")

        cameras = response.json()['cameras']

        log.debug("-------")
        for camera in cameras:
            log.debug(
                "Retrieved %s: %s",
                camera['name'],
                camera['camera_id']
            )
            camera_ids.append(camera['camera_id'])

        return camera_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e,
            response,
            "Cameras"
        )


def get_sites(x_verkada_token, x_verkada_auth, usr, site_session,
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
    :param site_session: The user session to use when making API calls.
    :type site_session: requests.Session
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
        log.debug("Requesting sites.")
        # print(url)
        response = site_session.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Sites JSON retrieved. Parsing and logging.")

        sites = response.json()['sites']

        log.debug("-------")
        for site in sites:
            log.debug("Retrieved %s: %s", site['siteId'], site['siteName'])
            site_ids.append(site['siteId'])

        return site_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e,
            response,
            "Sites"
        )


def list_ac(x_verkada_token, x_verkada_auth, usr, ac_session,
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
    :param ac_session: The user session to use when making API calls.
    :type ac_session: requests.Session
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
        response = ac_session.post(AC_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Access control JSON retrieved. Parsing and logging.")

        access_devices = response.json()['accessControllers']

        log.debug("-------")
        for controller in access_devices:
            log.debug(
                "Retrieved controller %s: %s",
                controller['name'],
                controller['deviceId']
            )

            access_ids.append(controller['deviceId'])

        return access_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e,
            response,
            "Access Control"
        )


def list_alarms(x_verkada_token, x_verkada_auth, usr, alarms_session,
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
    :param alarms_session: The user session to use when making API calls.
    :type alarms_session: requests.Session
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
        response = alarms_session.post(ALARM_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Alarm JSON retrieved. Parsing and logging.")

        alarm_devices = response.json()

        log.debug("-------")
        for dcs in alarm_devices['doorContactSensor']:
            log.debug(
                "Retrieved door contact sensor %s: %s",
                dcs['name'],
                dcs['deviceId']
            )
            dcs_ids.append(dcs['deviceId'])

        log.debug("-------")
        for gbs in alarm_devices['glassBreakSensor']:
            log.debug("Retrieved glass break sensor %s: %s",
                      gbs['name'],
                      gbs['deviceId']
                      )
            gbs_ids.append(gbs['deviceId'])

        log.debug("-------")
        for hub in alarm_devices['hubDevice']:
            log.debug("Retrieved glass break sensor %s: %s",
                      hub['name'],
                      hub['deviceId']
                      )
            hub_ids.append(hub['deviceId'])

        log.debug("-------")
        for keypad in alarm_devices['keypadHub']:
            log.debug("Retrieved glass break sensor %s: %s",
                      keypad['name'],
                      keypad['deviceId']
                      )
            hub_ids.append(keypad['deviceId'])

        log.debug("-------")
        for ms in alarm_devices['motionSensor']:
            log.debug("Retrieved glass break sensor %s: %s",
                      ms['name'],
                      ms['deviceId']
                      )
            ms_ids.append(ms['deviceId'])

        log.debug("-------")
        for pb in alarm_devices['panicButton']:
            log.debug("Retrieved glass break sensor %s: %s",
                      pb['name'],
                      pb['deviceId']
                      )
            pb_ids.append(pb['deviceId'])

        log.debug("-------")
        for ws in alarm_devices['waterSensor']:
            log.debug("Retrieved glass break sensor %s: %s",
                      ws['name'],
                      ws['deviceId']
                      )
            ws_ids.append(ws['deviceId'])

        log.debug("-------")
        for wr in alarm_devices['wirelessRelay']:
            log.debug("Retrieved glass break sensor %s: %s",
                      wr['name'],
                      wr['deviceId']
                      )
            wr_ids.append(wr['deviceId'])

        return dcs_ids, gbs_ids, hub_ids, ms_ids, pb_ids, ws_ids, wr_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(e, response, "Alarms")


def list_viewing_stations(x_verkada_token, x_verkada_auth, usr, vx_session,
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
    :param vx_session: The user session to use when making API calls.
    :type vx_session: requests.Session
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: An array of archived viewing station device IDs.
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
        response = vx_session.post(VX_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Viewing station JSON retrieved. Parsing and logging.")

        vx_devices = response.json()['viewingStations']

        log.debug("-------")
        for vx in vx_devices:
            vx_grid_data = vx['gridData']
            log.debug(
                "Retrieved viewing station %s: %s",
                vx_grid_data['name'],
                vx['viewingStationId']
            )
            vx_ids.append(vx['viewingStationId'])

        return vx_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e,
            response,
            "Viewing Stations"
        )


def list_gateways(x_verkada_token, x_verkada_auth, usr, gc_session,
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
    :param gc_session: The user session to use when making API calls.
    :type gc_session: requests.Session
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
        response = gc_session.post(GC_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Cellular gateways JSON retrieved. Parsing and logging.")

        gc_devices = response.json()

        log.debug("-------")
        for gc in gc_devices:
            log.debug(
                "Retrieved cellular gateway %s: %s",
                gc['name'],
                gc['device_id']
            )
            gc_ids.append(gc['device_id'])

        return gc_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e,
            response,
            "Cellular Gateways"
        )


def list_sensors(x_verkada_token, x_verkada_auth, usr, sv_session,
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
    :param sv_session: The user session to use when making API calls.
    :type sv_session: requests.Session
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
        response = sv_session.post(SV_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Environmental Sensor JSON retrieved. Parsing and logging.")

        sv_devices = response.json()['sensorDevice']

        log.debug("-------")
        for sv in sv_devices:
            log.debug(
                "Retrieved Environmental Sensor %s: %s",
                sv['name'],
                sv['deviceId']
            )
            sv_ids.append(sv['deviceId'])

        return sv_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e,
            response,
            "Environmental Sensors"
        )


def list_horns(x_verkada_token, x_verkada_auth, usr, bz_session,
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
    :param bz_session: The user session to use when making API calls.
    :type bz_session: requests.Session
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
        response = bz_session.post(BZ_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Horn speakers JSON retrieved. Parsing and logging.")

        bz_devices = response.json()['garfunkel']

        log.debug("-------")
        for bz in bz_devices:
            log.debug(
                "Retrieved horn speaker %s: %s",
                bz['name'],
                bz['deviceId']
            )
            bz_ids.append(bz['deviceId'])

        return bz_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e,
            response,
            "BZ11 Horn Speakers"
        )


def list_desk_stations(x_verkada_token, usr, ds_session,
                       org_id=ORG_ID):
    """
    Lists all desk stations.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param ds_session: The user session to use when making API calls.
    :type ads_session: requests.Session
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: An array of registered desk station apps on iPads.
    :rtype: list
    """
    headers = {
        "x-verkada-organization-id": org_id,
        "x-verkada-token": x_verkada_token,
        "x-verkada-user-id": usr
    }

    desk_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting desk stations.")
        response = ds_session.get(DESK_URL, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Desk station JSON retrieved. Parsing and logging.")

        desk_stations = response.json()["deskApps"]

        log.debug("-------")
        for ds in desk_stations:
            log.debug(
                "Retrieved Desk Station %s: %s",
                ds['name'],
                ds['deviceId']
            )
            desk_ids.append(ds['deviceId'])

        return desk_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e,
            response,
            "Desk Stations"
        )


def list_guest(x_verkada_token, x_verkada_auth, usr, guest_session,
               org_id=ORG_ID, sites=None):
    """
    Lists all guest printers and iPads.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param guest_session: The user session to use when making API calls.
    :type guest_session: requests.Session
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :param sites: The list of site IDs to check in.
    :type sites: list, optional
    :return: An array of registered iPads with Verkada Guest software and
    any printers associated with the Verkada Guest platform. Returns iPad_ids
    followed by printer_ids.
    :rtype: list
    """
    headers = {
        "x-verkada-organization-id": org_id,
        "x-verkada-token": x_verkada_token,
        "x-verkada-user-id": usr
    }

    ipad_ids, printer_ids = [], []

    if not sites:
        sites = get_sites(x_verkada_token, x_verkada_auth,
                          usr, guest_session, org_id)

    try:
        # Request the JSON archive library
        log.debug("Requesting guest information.")
        for site in sites:
            url = IPAD_URL + site
            response = guest_session.get(url, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            log.debug("Guest JSON retrieved. Parsing and logging.")

            guest_devices = response.json()

            log.debug("-------")
            log.debug("Retrieving iPads for site %s.", site)
            for ipad in guest_devices['devices']:
                log.debug(
                    "Retrieved Guest iPad %s: %s",
                    ipad['name'],
                    ipad['deviceId']
                )
                ipad_ids.append(ipad['deviceId'])
            log.debug("IPads retrieved.")

            log.debug("-------")
            log.debug("Retrieving printers for site %s.", site)
            for printer in guest_devices['printers']:
                log.debug(
                    "Retrieved guest printer %s: %s",
                    printer['name'],
                    printer['printerId']
                )
                printer_ids.append(printer['printerId'])
            log.debug("Pritners retrieved.")

        return ipad_ids, printer_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e,
            response,
            "Sites"
        )


def list_acls(x_verkada_token, usr, acl_session,
              org_id=ORG_ID):
    """
    Lists all access control levels.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param usr: The user ID for a valid user in the Verkad organization.
    :type usr: str
    :param acl_session: The user session to use when making API calls.
    :type acl_session: requests.Session
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    :return: An array of Verkada access control levels.
    :rtype: list
    """
    headers = {
        "x-verkada-organization-id": org_id,
        "x-verkada-token": x_verkada_token,
        "x-verkada-user-id": usr
    }

    acl_ids = []

    try:
        log.debug("Gathering access control levels.")
        response = acl_session.get(ACCESS_LEVELS, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Access control levels received.")

        acls = response.json()['schedules']

        log.debug("-------")
        for acl in acls:
            log.debug(
                "Retrieved %s: %s",
                acl['name'],
                acl['scheduleId']
            )
            acl_ids.append(acl['scheduleId'])
        log.debug("Access levels retrieved.")

        return acls, acl_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e,
            response,
            "Sites"
        )


##############################################################################
                                #   Main   #
##############################################################################


# Check if the script is being imported or ran directly
if __name__ == "__main__":

    with requests.Session() as session:
        start_run_time = time.time()  # Start timing the script
        try:
            # Initialize the user session.
            csrf_token, user_token, user_id = login_and_get_tokens(session)

            # Continue if the required information has been received
            if csrf_token and user_token and user_id:
                # Define the threads with arguments
                c_thread = create_thread_with_args(
                    list_cameras, [API_KEY, session])
                ac_thread = create_thread_with_args(
                    list_ac, [csrf_token, user_token, user_id, session])
                br_thread = create_thread_with_args(
                    list_alarms, [csrf_token, user_token, user_id, session])
                vx_thread = create_thread_with_args(
                    list_viewing_stations, [csrf_token, user_token, user_id,
                                            session])
                gc_thread = create_thread_with_args(
                    list_gateways, [csrf_token, user_token, user_id, session])
                sv_thread = create_thread_with_args(
                    list_sensors, [csrf_token, user_token, user_id, session])
                bz_thread = create_thread_with_args(
                    list_horns, [csrf_token, user_token, user_id, session])
                ds_thread = create_thread_with_args(
                    list_desk_stations, [csrf_token, user_id, session])
                guest_thread = create_thread_with_args(
                    list_guest, [csrf_token, user_token, user_id, session])
                acl_thread = create_thread_with_args(
                    list_acls, [csrf_token, user_id, session])

                threads = [c_thread, ac_thread, br_thread, vx_thread,
                           gc_thread, sv_thread, bz_thread, ds_thread, guest_thread,
                           acl_thread]

                for thread in threads:
                    thread.start()

                for thread in threads:
                    thread.join()

                for thread in threads:
                    print(thread)

            # Handles when the required credentials were not received
            else:
                log.critical(
                    "No credentials were provided during "
                    "the authentication process or audit log "
                    "could not be retrieved."
                )

            # Calculate the time take to run and post it to the log
            elapsed_time = time.time() - start_run_time
            log.info("-------")
            log.info("Total time to complete %.2fs.", elapsed_time)

        # Gracefully handle an interrupt
        except KeyboardInterrupt:
            log.warning(
                "\nKeyboard interrupt detected. Logging out & aborting..."
            )

        finally:
            if csrf_token and user_token:
                log.debug("Logging out.")
                logout(session, csrf_token, user_token)
            session.close()
            log.debug("Session closed.\nExiting...")
