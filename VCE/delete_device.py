"""
Author: Ian Young
Purpose: Reset a Verkada Command organization for use at VCE. An API key and
valid user credentials are needed to run this script. Please use EXTREME
caution when running because this will delete all devices from an org
without any additional warnings.
"""

# Import essential libraries
import logging
import threading
import time
import sys
from datetime import datetime
from os import getenv
from typing import Optional, Dict, List, Any

import colorama
import requests
from colorama import Fore, Style
from dotenv import load_dotenv

sys.path.append("/path/to/modules")
import VCE.gather_devices as gather_devices
from QoL import login_and_get_tokens, logout, custom_exceptions
from QoL.get_key import get_api_token

colorama.init(autoreset=True)  # Initialize colorized output

load_dotenv()  # Load credentials file

log = logging.getLogger()
log.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Set final, global credential variables
API_KEY = getenv("denver_key")
USERNAME = getenv("denver_user")
PASSWORD = getenv("denver_pass")
ORG_ID = getenv("denver_id")
TOTP = getenv("denver_secret")
TOKEN = get_api_token(API_KEY)

# Root API URL
ROOT = "https://api.command.verkada.com/vinter/v1/user/async"
SHARD = "?sharding=true"

# Set final, global URLs
# * POST
ACCESS_DECOM = (
    "https://vcerberus.command.verkada.com/access_device/decommission"
)
AKEYPADS_DECOM = (
    "https://alarms.command.verkada.com/device/keypad_hub/decommission"
)
APANEL_DECOM = "https://alarms.command.verkada.com/device/hub/decommission"
ASENSORS_DECOM = "https://alarms.command.verkada.com/device/sensor/delete"
CAMERA_DECOM = "https://vprovision.command.verkada.com/camera/decommission"
ENVIRONMENTAL_DECOM = (
    "https://vsensor.command.verkada.com/devices/decommission"
)
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
##################################  Misc  ####################################
##############################################################################


class RateLimiter:
    """
    The purpose of this class is to limit how fast multi-threaded actions are
    created to prevent hitting the API limit.
    """

    def __init__(
        self,
        rate_limit: float,
        max_events_per_sec: float = 10,
        pacing: float = 1,
    ):
        """
        Initialization of the rate limiter.

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
        self.start_time = 0
        self.event_count = 0
        self.pacing = pacing

    def acquire(self) -> bool:
        """
        States whether or not the program may create new threads or not.

        :return: Boolean value stating whether new threads may be made or not.
        :rtype: bool3
        """
        with self.lock:
            current_time = time.time()  # Define current time

            if not hasattr(self, "start_time"):
                # Check if attribute 'start_time' exists, if not, make it.
                self.start_time = int(current_time)
                self.event_count = int(self.pacing)
                return True

            # How much time has passed since starting
            elapsed_since_start = current_time - self.start_time

            # Check if it's been less than 1sec and less than 10 events have
            # been made.
            if (
                elapsed_since_start < self.pacing / self.rate_limit
                and self.event_count < self.max_events_per_sec
            ):
                self.event_count += 1
            elif elapsed_since_start >= self.pacing / self.rate_limit:
                self.start_time = int(current_time)
                self.event_count = 2
            else:
                # Calculate the time left before next wave
                remaining_time = self.pacing - (current_time - self.start_time)
                time.sleep(remaining_time)  # Wait before next wave

            return True


def run_thread_with_rate_limit(
    limited_threads: List[threading.Thread], rate_limit: float = 2
):
    """
    Run a thread with rate limiting.

    :param threads: A list of threads that need to be clocked.
    :type threads: list
    :param rate_limit: The value of how many threads may be made each sec.
    :type rate_limit: int
    :return: The thread that was created and ran.
    :rtype: thread
    """
    limiter = RateLimiter(rate_limit=rate_limit, max_events_per_sec=rate_limit)

    def run_thread(thread):
        limiter.acquire()

        log.debug(
            "%sStarting thread %s%s%s at time %s%s%s",
            Fore.LIGHTBLACK_EX,
            Fore.LIGHTYELLOW_EX,
            thread.name,
            Style.RESET_ALL,
            Fore.LIGHTBLACK_EX,
            datetime.now().strftime("%H:%M:%S"),
            Style.RESET_ALL,
        )

        thread.start()

    for thread in limited_threads:
        run_thread(thread)

    for thread in limited_threads:
        thread.join()


##############################################################################
################################  Requests  ##################################
##############################################################################


def delete_cameras(
    camera_session: requests.Session,
    x_verkada_token: str,
    usr: str,
    org_id: Optional[str] = ORG_ID,
):
    """
    Deletes all cameras from a Verkada organization.

    :param camera_session: The request session to use to make the call with.
    :type camera_session: requests.Session
    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param usr: The user ID of the authenticated user for a valid Verkada
    Command session.
    :type usr: str
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    """
    headers = {
        "x-verkada-organization-id": org_id,
        "x-verkada-token": x_verkada_token,
        "x-verkada-user-id": usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting cameras.")
        if TOKEN is not None:
            if cameras := gather_devices.list_cameras(TOKEN, camera_session):
                for camera in cameras:
                    body = {"cameraId": camera}

                    response = camera_session.post(
                        CAMERA_DECOM, headers=headers, json=body
                    )
                    response.raise_for_status()  # Raise an exception for HTTP errors

                log.info("%sCameras deleted.%s", Fore.GREEN, Style.RESET_ALL)

            else:
                log.warning(
                    "%sNo cameras were received.%s",
                    Fore.MAGENTA,
                    Style.RESET_ALL,
                )

    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Cameras"
        ) from e


def delete_sensors(
    x_verkada_token: str,
    x_verkada_auth: str,
    usr: str,
    alarm_session: requests.Session,
    org_id: Optional[str] = ORG_ID,
):
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
    :param alarm_session: The request session to use to make the call with.
    :type alarm_session: requests.Session
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    """
    alarm_threads = []

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr,
        "Content-Type": "application/json",
    }

    def delete_sensor(device_dict: List[Dict[str, str]]):
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
                "organizationId": org_id,
            }

            try:
                response = alarm_session.post(
                    ASENSORS_DECOM, headers=headers, json=data
                )
                response.raise_for_status()  # Raise an exception for HTTP errors

                log.debug(
                    "Deleted wireless sensor: %s", device.get("deviceType")
                )

            # Handle exceptions
            except requests.exceptions.RequestException as e:
                pline = "Wireless alarm sensor"
                raise custom_exceptions.APIExceptionHandler(e, response, pline)

    def delete_keypads(device_ids: List[str]):
        """
        Deletes a generic wireless alarm sensor from Verkada Command.

        :param device_dict: A dictionary of all wireless devices that includes
        their ID and the device type.
        :type device_dict: dict
        """
        processed_ids = set()
        for device_id in device_ids:
            if device_id not in processed_ids:
                data = {"deviceId": device_id, "organizationId": org_id}

                try:
                    log.debug("Running for %s", device_id)
                    response = alarm_session.post(
                        APANEL_DECOM, headers=headers, json=data
                    )
                    response.raise_for_status()  # Raise an exception for HTTP errors

                    processed_ids.add(device_id)
                    log.debug("Keypad deleted: %s", device_id)

                # Handle exceptions
                except requests.exceptions.HTTPError:
                    if response.status_code == 400:
                        log.debug("Trying as keypad.")
                        response = alarm_session.post(
                            AKEYPADS_DECOM, headers=headers, json=data
                        )

                        if response.status_code == 200:
                            log.debug(
                                "%sKeypad deleted successfully%s",
                                Fore.GREEN,
                                Style.RESET_ALL,
                            )

                        else:
                            log.warning(
                                "%sCould not delete %s%s\nStatus code: %s",
                                Fore.RED,
                                device_id,
                                Style.RESET_ALL,
                                response.status_code,
                            )

                except requests.exceptions.RequestException as e:
                    ptype = "Alarm keypad/panel"
                    raise custom_exceptions.APIExceptionHandler(
                        e, response, ptype
                    )

    def convert_to_dict(array, device_type) -> List[Dict[str, str]]:
        """
        Converts an array to a dictionary that contains the attribute
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
            device_dict_value = {"deviceId": device, "deviceType": device_type}
            device_dict.append(device_dict_value)

        return device_dict

    # Request all alarm sensors
    log.debug("Requesting alarm sensors.")
    dcs, gbs, hub, ms, pb, ws, wr = gather_devices.list_alarms(
        x_verkada_token, x_verkada_auth, usr, alarm_session, org_id
    )

    # Check if it is empty, if so, skip. If not, turn it into a dictionary.
    if dcs:
        door_thread = threading.Thread(
            target=delete_sensor,
            args=(convert_to_dict(dcs, "doorContactSensor"),),
        )
        alarm_threads.append(door_thread)
    if gbs:
        glass_thread = threading.Thread(
            target=delete_sensor,
            args=(convert_to_dict(gbs, "glassBreakSensor"),),
        )
        alarm_threads.append(glass_thread)
    if hub:
        keypad_thread = threading.Thread(target=delete_keypads, args=(hub,))
        alarm_threads.append(keypad_thread)
    if ms:
        motion_thread = threading.Thread(
            target=delete_sensor, args=(convert_to_dict(ms, "motionSensor"),)
        )
        alarm_threads.append(motion_thread)
    if pb:
        panic_thread = threading.Thread(
            target=delete_sensor, args=(convert_to_dict(pb, "panicButton"),)
        )
        alarm_threads.append(panic_thread)
    if ws:
        water_thread = threading.Thread(
            target=delete_sensor, args=(convert_to_dict(ws, "waterSensor"),)
        )
        alarm_threads.append(water_thread)
    if wr:
        relay_thread = threading.Thread(
            target=delete_sensor, args=(convert_to_dict(wr, "wirelessRelay"),)
        )
        alarm_threads.append(relay_thread)

    # Check if there are threads waiting to be ran.
    if alarm_threads:
        # Run the threads
        for thread in alarm_threads:
            thread.start()
        # Wait for them to finish
        for thread in alarm_threads:
            thread.join()

        log.info("%sAlarm sensors deleted.%s", Fore.GREEN, Style.RESET_ALL)

    else:
        log.warning(
            "%sNo alarm sensors were received.%s",
            Fore.MAGENTA,
            Style.RESET_ALL,
        )


def delete_panels(
    x_verkada_token: str,
    x_verkada_auth: str,
    usr: str,
    ac_session: requests.Session,
    org_id: Optional[str] = ORG_ID,
):
    """
    Deletes all access control panels from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param ac_session: The request session to use to make the call with.
    :type ac_session: requests.Session
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    """
    exempt: List[str] = []

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting Access control panels.")
        if panels := gather_devices.list_ac(
            x_verkada_token, x_verkada_auth, usr, ac_session, org_id
        ):
            for panel in panels:
                if panel not in exempt:
                    log.debug("Running for access control panel: %s", panel)

                    data = {"deviceId": panel}

                    response = ac_session.post(
                        ACCESS_DECOM, headers=headers, json=data
                    )
                    response.raise_for_status()  # Raise an exception for HTTP errors

            log.info(
                "%sAccess control panels deleted.%s",
                Fore.GREEN,
                Style.RESET_ALL,
            )

        else:
            log.warning(
                "%sNo Access control panels were received.%s",
                Fore.MAGENTA,
                Style.RESET_ALL,
            )

    except requests.exceptions.HTTPError:
        if response.status_code == 400:
            log.debug(
                "%sTrying %s as intercom.%s",
                Fore.MAGENTA,
                panel,
                Style.RESET_ALL,
            )
            delete_intercom(x_verkada_token, usr, panel, ac_session)
        else:
            log.error(
                "%sAccess control panel returned with a non-200 code: %s%s",
                Fore.RED,
                response.status_code,
                Style.RESET_ALL,
            )

    except requests.exceptions.RequestException as e:
        ptype = "Access control panel"
        raise custom_exceptions.APIExceptionHandler(e, response, ptype) from e


def delete_intercom(
    x_verkada_token: str,
    usr: str,
    device_id: str,
    icom_session: requests.Session,
    org_id: Optional[str] = ORG_ID,
):
    """
    Deletes all Intercoms from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param icom_session: The request session to use to make the call with.
    :type icom_session: requests.Session
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    """
    headers = {
        "x-verkada-organization-id": org_id,
        "x-verkada-token": x_verkada_token,
        "x-verkada-user-id": usr,
    }

    try:
        url = DESK_DECOM + device_id + SHARD

        log.debug("Running for intercom: %s", device_id)

        response = icom_session.delete(url, headers=headers)
        response.raise_for_status()  # Raise for HTTP errors

        log.info("%sIntercom deleted.%s", Fore.GREEN, Style.RESET_ALL)

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        ptype = "Intercom"
        raise custom_exceptions.APIExceptionHandler(e, response, ptype) from e


def delete_environmental(
    x_verkada_token: str,
    x_verkada_auth: str,
    usr: str,
    sv_session: requests.Session,
    org_id: Optional[str] = ORG_ID,
):
    """
    Deletes all environmental sensors from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param sv_session: The request session to use to make the call with.
    :type sv_session: requests.Session
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    """
    params = {"organizationId": org_id}

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting environmental sensors.")
        if sv_ids := gather_devices.list_sensors(
            x_verkada_token, x_verkada_auth, usr, sv_session, org_id
        ):
            for sensor in sv_ids:
                data = {"deviceId": sensor}

                log.info("Running for environmental sensor %s", sensor)

                response = sv_session.post(
                    ENVIRONMENTAL_DECOM,
                    json=data,
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()  # Raise an exception for HTTP errors

            log.info(
                "%sEnvironmental sensors deleted.%s",
                Fore.GREEN,
                Style.RESET_ALL,
            )

        else:
            log.warning(
                "%sNo environmental sensors were received.%s",
                Fore.MAGENTA,
                Style.RESET_ALL,
            )

    except requests.exceptions.RequestException as e:
        ptype = "Environmental sensor"
        raise custom_exceptions.APIExceptionHandler(e, response, ptype) from e


def delete_guest(
    x_verkada_token: str,
    x_verkada_auth: str,
    usr: str,
    guest_session: requests.Session,
    org_id: Optional[str] = ORG_ID,
):
    """
    Deletes all Guest devices from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param guest_session: The request session to use to make the call with.
    :type guest_session: requests.Session
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    """
    params = {"organizationId": org_id}

    headers = {
        "X-CSRF-Token": x_verkada_token,
        "X-Verkada-Auth": x_verkada_auth,
        "User": usr,
    }

    try:
        # Request the JSON library for Sites
        log.debug("Initiating site request.")
        sites = gather_devices.get_sites(
            x_verkada_token, x_verkada_auth, usr, guest_session, org_id
        )

        # Request the JSON library for Guest
        log.debug("Initiating Guest requests.")
        ipad_ids, printer_ids = gather_devices.list_guest(
            x_verkada_token, x_verkada_auth, usr, guest_session, org_id, sites
        )

        for site in sites:
            ipad_present = True
            printer_present = True

            if ipad_ids:
                for ipad in ipad_ids:
                    url = f"{GUEST_IPADS_DECOM}{site}?deviceId={ipad}"

                    log.debug("Running for iPad: %s", ipad)

                    response = guest_session.delete(
                        url, headers=headers, params=params
                    )
                    response.raise_for_status()  # Raise for HTTP errors

                log.info(
                    "%siPads deleted for site %s%s",
                    Fore.GREEN,
                    site,
                    Style.RESET_ALL,
                )

            else:
                ipad_present = False
                log.debug("No iPads present.")

            if printer_ids:
                for printer in printer_ids:
                    url = f"{GUEST_PRINTER_DECOM}{site}?printerId={printer}"

                    log.debug("Running for printer: %s", printer)

                    response = guest_session.delete(
                        url, headers=headers, params=params
                    )
                    response.raise_for_status()  # Raise for HTTP errors

                log.info(
                    "%sPrinters deleted for site %s%s",
                    Fore.GREEN,
                    site,
                    Style.RESET_ALL,
                )

            else:
                printer_present = False
                log.debug("No printers present.")

            if not ipad_present and not printer_present:
                log.warning(
                    "%sNo Guest devices were received for site %s%s.",
                    Fore.MAGENTA,
                    site,
                    Style.RESET_ALL,
                )

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        ptype = "Guest"
        raise custom_exceptions.APIExceptionHandler(e, response, ptype) from e


def delete_acls(
    x_verkada_token: str,
    usr: str,
    acl_session: requests.Session,
    org_id: Optional[str] = ORG_ID,
):
    """
    Deletes all access control levels from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param acl_session: The request session to use to make the call with.
    :type acl_session: requests.Session
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    """

    def find_schedule_by_id(
        schedule_id, schedules
    ) -> Optional[Dict[str, Any]]:
        for schedule in schedules:
            if schedule["scheduleId"] == schedule_id:
                return schedule
        return None

    headers = {
        "x-verkada-organization-id": org_id,
        "x-verkada-token": x_verkada_token,
        "x-verkada-user-id": usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Initiating request for access control levels.")
        acls, acl_ids = gather_devices.list_acls(
            x_verkada_token, usr, acl_session, org_id
        )

        if acls is not None and acl_ids is not None:
            for acl in acl_ids:
                if schedule := find_schedule_by_id(acl, acls):
                    log.info("Running for access control level %s", acl)
                    schedule["deleted"] = True
                    data = {"sitesEnabled": True, "schedules": [schedule]}

                    response = acl_session.put(
                        ACCESS_LEVEL_DECOM, json=data, headers=headers
                    )
                    response.raise_for_status()  # Raise an exception for HTTP errors

                log.info(
                    "%sAccess control levels deleted.%s",
                    Fore.GREEN,
                    Style.RESET_ALL,
                )

        else:
            log.warning(
                "%sNo access control levels were received.%s",
                Fore.MAGENTA,
                Style.RESET_ALL,
            )

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        ptype = "Access control levels"
        raise custom_exceptions.APIExceptionHandler(e, response, ptype)


def delete_desk_station(
    x_verkada_token: str,
    usr: str,
    ds_session: requests.Session,
    org_id: Optional[str] = ORG_ID,
):
    """
    Deletes all Guest devices from a Verkada organization.

    :param x_verkada_token: The csrf token for a valid, authenticated session.
    :type x_verkada_token: str
    :param x_verkada_auth: The authenticated user token for a valid Verkada
    session.
    :type x_verkada_auth: str
    :param ds_session: The request session to use to make the call with.
    :type ds_session: requests.Session
    :param org_id: The organization ID for the targeted Verkada org.
    :type org_id: str, optional
    """
    headers = {
        "x-verkada-organization-id": org_id,
        "x-verkada-token": x_verkada_token,
        "x-verkada-user-id": usr,
    }

    try:
        # Request the JSON library for Desk Station
        log.debug("Initiating Desk Station requests.")
        if ds_ids := gather_devices.list_desk_stations(
            x_verkada_token, usr, ds_session, org_id
        ):
            for desk_station in ds_ids:
                url = DESK_DECOM + desk_station + SHARD

                log.debug(
                    "%sRunning for Desk Station: %s%s",
                    Fore.GREEN,
                    desk_station,
                    Style.RESET_ALL,
                )

                response = ds_session.delete(url, headers=headers)
                response.raise_for_status()  # Raise for HTTP errors

                log.info(
                    "%sDesk Stations deleted.%s", Fore.GREEN, Style.RESET_ALL
                )

    except requests.exceptions.RequestException as e:
        ptype = "Desk Station"
        raise custom_exceptions.APIExceptionHandler(e, response, ptype) from e


##############################################################################
##################################  Main  ####################################
##############################################################################


if __name__ == "__main__":
    csrf_token, user_token, user_id = None, None, None
    start_run_time = time.time()  # Start timing the script
    with requests.Session() as session:
        try:
            # Initialize the user session.
            if USERNAME and PASSWORD and ORG_ID:
                csrf_token, user_token, user_id = login_and_get_tokens(
                    session, USERNAME, PASSWORD, ORG_ID, TOTP
                )

                # Continue if the required information has been received
                if csrf_token and user_token and user_id:
                    # Place each element in their own thread to speed up runtime
                    camera_thread = threading.Thread(
                        target=delete_cameras,
                        args=(
                            session,
                            csrf_token,
                            user_token,
                        ),
                    )

                    alarm_thread = threading.Thread(
                        target=delete_sensors,
                        args=(
                            csrf_token,
                            user_token,
                            user_id,
                            session,
                        ),
                    )

                    ac_thread = threading.Thread(
                        target=delete_panels,
                        args=(
                            csrf_token,
                            user_token,
                            user_id,
                            session,
                        ),
                    )

                    sv_thread = threading.Thread(
                        target=delete_environmental,
                        args=(
                            csrf_token,
                            user_token,
                            user_id,
                            session,
                        ),
                    )

                    guest_thread = threading.Thread(
                        target=delete_guest,
                        args=(
                            csrf_token,
                            user_token,
                            user_id,
                            session,
                        ),
                    )

                    acl_thread = threading.Thread(
                        target=delete_acls,
                        args=(
                            csrf_token,
                            user_id,
                            session,
                        ),
                    )

                    desk_thread = threading.Thread(
                        target=delete_desk_station,
                        args=(
                            csrf_token,
                            user_id,
                            session,
                        ),
                    )

                    # # List all the threads to be ran
                    threads = [
                        camera_thread,
                        alarm_thread,
                        ac_thread,
                        sv_thread,
                        guest_thread,
                        acl_thread,
                        desk_thread,
                    ]

                    # Start the clocked threads
                    run_thread_with_rate_limit(threads)

            # Handles when the required credentials were not received
            else:
                log.critical(
                    "%sNo credentials were provided during "
                    "the authentication process or audit log "
                    "could not be retrieved.%s",
                    Fore.MAGENTA,
                    Style.RESET_ALL,
                )

            # Calculate the time take to run and post it to the log
            elapsed_time = time.time() - start_run_time
            log.info("-------")
            log.info(
                "Total time to complete %s%.2fs%s",
                Fore.CYAN,
                elapsed_time,
                Style.RESET_ALL,
            )

        # Gracefully handle an interrupt
        except KeyboardInterrupt:
            print(
                f"{Fore.RED}\nKeyboard interrupt detected. "
                f"Logging out & aborting...{Style.RESET_ALL}"
            )

        finally:
            log.debug("Logging out.")
            if csrf_token and user_token:
                logout(session, csrf_token, user_token, ORG_ID)
            session.close()
            log.debug("Session closed.\nExiting...")
