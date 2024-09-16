"""
Author: Ian Young
Purpose: Iterate through all archives that are visible to a user and delete
them. This is ONLY to be used to keep a given org clean. Extreme caution is
advised since the changes this script will make to the org cannot be undone
once made.
"""

# Import essential libraries
import json
import threading
import time
from typing import List
from os import getenv

import requests
from dotenv import load_dotenv
from tinydb import TinyDB, Query

from tools import (
    log,
    login_and_get_tokens,
    logout,
    custom_exceptions,
    SharedParams,
)
from tools.api_endpoints import (
    AC_URL,
    ALARM_URL,
    VX_URL,
    GC_URL,
    SV_URL,
    BZ_URL,
    GET_CAMERA_DATA,
    GET_AUDIT_LOGS,
    GET_SITES,
    set_org_id,
)

load_dotenv()  # Load credentials file

DB_PATH = "devices.json"
Device = Query()
db = TinyDB(DB_PATH)

# Set final, global credential variables
API_KEY = getenv("")
USERNAME = getenv("")
PASSWORD = getenv("")
ORG_ID = getenv("")
TOTP = getenv("")

# Set final, global URLs
urls = set_org_id(ORG_ID)
DESK_URL = urls["DESK_URL"]
IPAD_URL = urls["IPAD_URL"]
ACCESS_LEVELS = urls["ACCESS_LEVELS"]

devices_serials = []
ARRAY_LOCK = threading.Lock()


##############################################################################
#################################   Requests   ###############################
##############################################################################


def get_audit_log(audit_session, audit_start, audit_end):
    """
    Retrieve a list of events from the Verkada Command audit log.

    :param audit_session: The authenticated session to use when making calls.
    :type audit_session: requests.Session
    :param audit_start: The time the audit log should start at.
    :type audit_start: int
    :param audit_end: The time the audit log should end at.
    :type audit_end: int
    :return: The dictionary of audit log events.
    :rtype: list
    """
    headers = {
        "x-api-key": getenv("LAB_KEY"),
        "Content-Type": "application/json",
    }
    url = f"{GET_AUDIT_LOGS}?start_time={audit_start}&end_time={audit_end}"
    log.debug("Requesting logs.")

    try:
        response = audit_session.get(url, headers=headers)
        response.raise_for_status()
        log.debug("Logs retrieved.")

        return response.json()["audit_logs"]

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Audit Log"
        ) from e


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
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    log.debug("Requesting camera data")

    try:
        response = camera_session.get(GET_CAMERA_DATA, headers=headers)
        response.raise_for_status()
        log.debug("-------")
        log.debug("Camera data retrieved.")

        cameras = response.json()["cameras"]

        log.debug("-------")
        log.debug("Cameras:")
        for camera in cameras:
            log.debug(camera["serial"])
            with ARRAY_LOCK:
                devices_serials.append(camera["serial"])
                build_db(camera["serial"], "camera")

        return cameras

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Cameras"
        ) from e


def get_sites(params: SharedParams):
    """
    Lists all Verkada Guest sites.

    :param params: A class with frequently used variable when making
        requests.
    :type params: SharedParams
    :return: An array of all Verkada sites.
    :rtype: list
    """
    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    url = GET_SITES + params.org_id if GET_SITES and params.org_id else ""
    try:
        # Request the JSON archive library
        log.debug("Requesting sites.")
        # log.debug(url)
        response = params.session.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Sites JSON retrieved. Parsing and logging.")

        sites = response.json()["sites"]

        log.debug("-------")
        log.debug("Sites:")
        for site in sites:
            log.debug("Retrieved %s: %s", site["siteId"], site["siteName"])
            with ARRAY_LOCK:
                devices_serials.append(sites["siteId"])
                build_db(sites["siteId"], "site")

        return sites

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Sites"
        ) from e


def list_ac(params: SharedParams):
    """
    Lists all access control devices.

    :param params: A class with frequently used variable when making
        requests.
    :type params: SharedParams
    :return: An array of door controller device IDs.
    :rtype: list
    """
    body = {"organizationId": params.org_id}

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting access control devices.")
        response = params.session.post(AC_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Access control JSON retrieved. Parsing and logging.")

        access_devices = response.json()["accessControllers"]

        log.debug("-------")
        log.debug("Access Controllers:")
        for controller in access_devices:
            log.debug(
                "Retrieved controller %s: %s",
                controller["name"],
                controller["deviceId"],
            )
            with ARRAY_LOCK:
                devices_serials.append(controller["serialNumber"])
                build_db(controller["serialNumber"], "controllers")

        return access_devices

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Access Control"
        ) from e


def build_device(device_name, device_type, serial, key, devices):
    """
    Build a device in the system.

    Args:
        device_name (str): The name of the device.
        device_type (str): The type of the device.
        serial (str): The serial number of the device.
        key (str): The key of the device.
        devices (dict): Dictionary of devices to search for the
        device type.

    Returns:
        None
    """
    log.debug("-------")
    log.debug("%s:", device_name)
    for dev in devices[device_type]:
        log.debug(dev[serial])
        with ARRAY_LOCK:
            devices_serials.append(dev[serial])
            build_db(dev[serial], key)


def list_alarms(params: SharedParams):
    """
    Lists all alarm devices.

    :param params: A class with frequently used variable when making
        requests.
    :type params: SharedParams
    :return: Arrays of each wireless alarm sensor type device IDs.
    :rtype: lists
    """
    body = {"organizationId": params.org_id}

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting alarm devices.")
        response = params.session.post(ALARM_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Alarm JSON retrieved. Parsing and logging.")

        alarm_devices = response.json()
        build_device(
            "Door Contacts",
            "doorContactSensor",
            "serialNumber",
            "door_contact",
            alarm_devices,
        )
        build_device(
            "Glass Break",
            "glassBreakSensor",
            "serialNumber",
            "glass_break",
            alarm_devices,
        )
        build_device(
            "Hub devices",
            "hubDevice",
            "claimedSerialNumber",
            "hub_device",
            alarm_devices,
        )
        build_device(
            "Keypads",
            "keypadHub",
            "claimedSerialNumber",
            "keypad",
            alarm_devices,
        )
        build_device(
            "Motion Sensors",
            "motionSensor",
            "serialNumber",
            "motion_sensor",
            alarm_devices,
        )
        build_device(
            "Panic Buttons",
            "panicButton",
            "serialNumber",
            "panic_button",
            alarm_devices,
        )
        build_device(
            "Water Sensors",
            "waterSensor",
            "serialNumber",
            "water_sensor",
            alarm_devices,
        )
        build_device(
            "Wireless Relays",
            "wirelessRelay",
            "serialNumber",
            "wireless_relay",
            alarm_devices,
        )

        return alarm_devices

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Alarms"
        ) from e


def list_viewing_stations(params: SharedParams):
    """
    Lists all viewing stations.

    :param params: A class with frequently used variable when making
        requests.
    :type params: SharedParams
    :return: An array of archived viewing station device IDs.
    :rtype: list
    """
    body = {"organizationId": params.org_id}

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting viewing stations.")
        response = params.session.post(VX_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Viewing station JSON retrieved. Parsing and logging.")

        vx_devices = response.json()["viewingStations"]

        log.debug("-------")
        log.debug("Viewing stations:")
        for vx in vx_devices:
            log.debug(vx["claimedSerialNumber"])
            with ARRAY_LOCK:
                devices_serials.append(vx["claimedSerialNumber"])
                build_db(vx["claimedSerialNumber"], "viewing_station")

        return vx_devices

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Viewing Station"
        ) from e


def list_gateways(params: SharedParams):
    """
    Lists all cellular gateways.

    :param params: A class with frequently used variable when making
        requests.
    :type params: SharedParams
    :return: An array of gateway device IDs.
    :rtype: list
    """
    body = {"organizationId": params.org_id}

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting cellular gateways.")
        response = params.session.post(GC_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Cellular gateways JSON retrieved. Parsing and logging.")

        gc_devices = response.json()

        log.debug("-------")
        log.debug("Gateways:")
        for gc in gc_devices:
            log.debug(gc["claimed_serial_number"])
            with ARRAY_LOCK:
                devices_serials.append(gc["claimed_serial_number"])
                build_db(gc["claimed_serial_number"], "gateway")

        return gc_devices

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Cellular Gateways"
        ) from e


def list_sensors(params: SharedParams):
    """
    Lists all environmental sensors.

    :param params: A class with frequently used variable when making
        requests.
    :type params: SharedParams
    :return: An array of environmental sensor device IDs.
    :rtype: list
    """
    body = {"organizationId": params.org_id}

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting environmental sensors.")
        response = params.session.post(SV_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Environmental Sensor JSON retrieved. Parsing and logging.")

        sv_devices = response.json()["sensorDevice"]

        log.debug("-------")
        log.debug("Environmental sensors:")
        for sv in sv_devices:
            log.debug(sv["claimedSerialNumber"])
            with ARRAY_LOCK:
                devices_serials.append(sv["claimedSerialNumber"])
                build_db(sv["claimedSerialNumber"], "environmental_sensor")

        return sv_devices

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Environmental Sensors "
        ) from e


def list_horns(params: SharedParams):
    """
    Lists all BZ horn speakers.

    :param params: A class with frequently used variable when making
        requests.
    :type params: SharedParams
    :return: An array of BZ11 device IDs.
    :rtype: list
    """
    body = {"organizationId": params.org_id}

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting horn speakers.")
        response = params.session.post(BZ_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Horn speakers JSON retrieved. Parsing and logging.")

        bz_devices = response.json()["garfunkel"]

        log.debug("-------")
        log.debug("Horn speakers (BZ11):")
        for bz in bz_devices:
            log.debug(bz["serialNumber"])
            with ARRAY_LOCK:
                devices_serials.append(bz["serialNumber"])
                build_db(bz["serialNumber"], "horn_speaker")

        return bz_devices

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "BZ11 Horn Speakers"
        ) from e


def list_desk_stations(params: SharedParams):
    """
    Lists all desk stations.

    :param params: A class with frequently used variable when making
        requests.
    :type params: SharedParams
    :return: An array of registered desk station apps on iPads.
    :rtype: list
    """
    headers = {
        "x-verkada-organization-id": params.org_id,
        "x-verkada-token": params.x_verkada_token,
        "x-verkada-user-id": params.usr,
    }

    desk_ids: List[str] = []

    try:
        # Request the JSON archive library
        log.debug("Requesting desk stations.")
        response = params.session.get(DESK_URL, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Desk station JSON retrieved. Parsing and logging.")

        desk_stations = response.json()["deskApps"]

        log.debug("-------")
        for ds in desk_stations:
            log.debug(
                "Retrieved Desk Station %s: %s", ds["name"], ds["deviceId"]
            )
            with ARRAY_LOCK:
                devices_serials.append(ds["serialNumber"])
                build_db(ds["serialNumber"], "desk_station")

        return desk_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Desk Stations"
        ) from e


def list_guest(
    params: SharedParams,
    sites=None,
):
    """
    Lists all guest printers and iPads.

    :param params: A class with frequently used variable when making
        requests.
    :type params: SharedParams
    :param sites: The list of site IDs to check in.
    :type sites: list, optional
    :return: An array of registered iPads with Verkada Guest software and
    any printers associated with the Verkada Guest platform. Returns iPad_ids
    followed by printer_ids.
    :rtype: list
    """
    headers = {
        "x-verkada-organization-id": params.org_id,
        "x-verkada-token": params.x_verkada_token,
        "x-verkada-user-id": params.usr,
    }

    ipad_ids: List[str] = []
    printer_ids: List[str] = []

    if not sites:
        sites = get_sites(params)

    try:
        # Request the JSON archive library
        log.debug("Requesting guest information.")
        for site in sites:
            url = IPAD_URL + site
            response = params.session.get(url, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            log.debug("Guest JSON retrieved. Parsing and logging.")

            guest_devices = response.json()

            log.debug("-------")
            log.debug("Retrieving iPads for site %s.", site)
            for ipad in guest_devices["devices"]:
                log.debug(
                    "Retrieved Guest iPad %s: %s",
                    ipad["name"],
                    ipad["deviceId"],
                )
                with ARRAY_LOCK:
                    devices_serials.append(ipad["serialNumber"])
                    build_db(ipad["serialNumber"], "guest_ipad")
            log.debug("IPads retrieved.")

            log.debug("-------")
            log.debug("Retrieving printers for site %s.", site)
            for printer in guest_devices["printers"]:
                log.debug(
                    "Retrieved guest printer %s: %s",
                    printer["name"],
                    printer["printerId"],
                )
                with ARRAY_LOCK:
                    devices_serials.append(printer["serialNumber"])
                    build_db(printer["serialNumber"], "guest_printer")
            log.debug("Printers retrieved.")

        return ipad_ids, printer_ids

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Sites"
        ) from e


##############################################################################
###############################   Database   #################################
##############################################################################


def build_db(serial, device_type):
    """
    Builds a database of all serial numbers in a Verkada Organization.

    :param serial: The serial number of a particular device to be added.
    :type serial: str
    :param device_type: The product line of the device that is being added.
    :type device_type: str
    """
    log.debug("Adding table")
    device_info = {
        "serial": serial,
        "product_line": device_type,
        "time_removed": "",
        "who_removed": "",
    }
    if db.get(Device.serial == str(serial)):
        log.debug("Found existing device.")
        db.update(device_info, Device.serial == str(serial))
    else:
        db.insert(device_info)
    log.debug("Device is currently in the table.")


def get_devices_removed_from_org(serials):
    """
    Checks against the table created by TinyDB to see which cameras have been
    removed since the last time the script was ran.

    :param serial: The serial number of a particular device in a Command org.
    :type serial: str
    """

    make_verbose("Serials Currently in Org", serials)
    stored_devices = db.search(Device.serial.exists())
    stored_serials = [device["serial"] for device in stored_devices]

    make_verbose("Stored Serials", stored_serials)
    devices_not_in_sweep = db.search(~Device.serial.one_of(serials))

    make_verbose("Devices not in sweep", devices_not_in_sweep)
    for camera in devices_not_in_sweep:
        if camera["time_removed"] == "":
            camera["time_removed"] = int(time.time())
            db.update(camera, Device.serial == str(camera["serial"]))
            log.debug("--------------------")  # Aesthetic dividing line
            log.debug(json.dumps(camera, indent=2))

    return devices_not_in_sweep


def make_verbose(arg0, arg1):
    """
    Perform weather-related actions based on the snowfall data at a
    specified latitude and longitude.

    Returns:
        None
    """
    log.info("--------------------")  # Aesthetic dividing line
    log.info(arg0)
    log.info(arg1)


def get_device_removed_user(serial, audit_log_events):
    """
    Will retrieve the user who removed a device from a Verkada Command
    organization.

    :param serial: The serial number of the Verkada device that was removed.
    :type serial: str
    :param audit_log_events: The audit log of actions taken in Verkada Command.
    :type audit_log_events: dict
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
        device_results = db.search(Device.camera_id == device_id)

        if len(device_results) > 0:
            device_details = device_results[0]
        else:
            return None

        log.debug(device_details)
        if device_details["serial"] == serial:
            user_email = event["user_email"]
            return user_email

        return None

    log.info("--------------------")  # Aesthetic dividing line
    log.info("Finding who removed %s.", {serial})

    devices_uninstalled = list(
        filter(
            lambda log: log["event_name"] == "Devices Uninstalled",
            audit_log_events,
        )
    )

    for event in devices_uninstalled:
        event_devices = event["devices"]
        if len(event_devices) < 1:
            return None
        for dvc in event_devices:
            correct_event = is_correct_event(str(dvc["device_id"]))

            if correct_event:
                log.info("Correct audit event:")
                log.info(correct_event)
                return correct_event


##############################################################################
#################################   Main   ###################################
##############################################################################


# Check if the script is being imported or ran directly
if __name__ == "__main__":
    TIME_FRAME = 3600

    with requests.Session() as gather_session:
        start_run_time = time.time()  # Start timing the script
        try:
            # Initialize the user session.
            csrf_token, user_token, user_id = None, None, None  # Initialize
            if USERNAME and PASSWORD and ORG_ID:
                csrf_token, user_token, user_id = login_and_get_tokens(
                    gather_session, USERNAME, PASSWORD, ORG_ID, TOTP
                )
            timestamp = int(time.time())
            # Starting time frame is an hour ago because the script runs hourly
            start_time = timestamp - TIME_FRAME
            # If the device was removed within the past hour, make sure the function
            # doesn't try to search for a log in the future.
            end_time = (
                timestamp + TIME_FRAME
                if timestamp + TIME_FRAME < int(time.time())
                else int(time.time())
            )
            audit_log = get_audit_log(gather_session, start_time, end_time)

            # Continue if the required information has been received
            if csrf_token and user_token and user_id and audit_log:
                runtime_params = SharedParams(
                    gather_session, csrf_token, user_token, user_id, ORG_ID
                )
                log.debug("Retrieving cameras.")
                c_thread = threading.Thread(target=list_cameras)
                log.debug("Cameras retrieved")

                log.debug("Retrieving Access controllers.")
                ac_thread = threading.Thread(
                    target=list_ac,
                    args=(runtime_params,),
                )
                log.debug("Controllers retrieved.")

                log.debug("Retrieving Alarm devices.")
                br_thread = threading.Thread(
                    target=list_alarms,
                    args=(runtime_params,),
                )
                log.debug("Alarm devices retrieved.")

                log.debug("Retrieving viewing stations.")
                vx_thread = threading.Thread(
                    target=list_viewing_stations,
                    args=(runtime_params,),
                )
                log.debug("Viewing stations retrieved.")

                log.debug("Retrieving cellular gateways.")
                gc_thread = threading.Thread(
                    target=list_gateways,
                    args=(runtime_params,),
                )
                log.debug("Cellular gateways retrieved.")

                log.debug("Retrieving environmental sensors.")
                sv_thread = threading.Thread(
                    target=list_sensors,
                    args=(runtime_params,),
                )
                log.debug("Environmental sensors retrieved.")

                log.debug("Retrieving horn speakers.")
                bz_thread = threading.Thread(
                    target=list_horns,
                    args=(runtime_params,),
                )
                log.debug("Horn speakers retrieved.")

                threads = [
                    c_thread,
                    ac_thread,
                    br_thread,
                    vx_thread,
                    gc_thread,
                    sv_thread,
                    bz_thread,
                ]

                for thread in threads:
                    thread.start()

                for thread in threads:
                    thread.join()

            # Handles when the required credentials were not received
            else:
                log.critical(
                    "No credentials were provided during "
                    "the authentication process or audit log "
                    "could not be retrieved."
                )

            # Calculate the time take to run and post it to the log

            if audit_log is not None:
                log.info("--------------------")  # Aesthetic dividing line
                log.info("Got Audit log")
                removed_devices = get_devices_removed_from_org(devices_serials)
                for device in removed_devices:
                    user = get_device_removed_user(device["serial"], audit_log)
                    if user is not None:
                        # Aesthetic dividing line
                        log.info("--------------------")
                        log.info("%s deleted %s", user, device["serial"])
                        device["time_removed"] = int(time.time())
                        device["who_removed"] = user
                        db.update(
                            device, Device.serial == str(device["serial"])
                        )
                        log.debug("Reminder to add device.")
                    else:
                        # Aesthetic dividing line
                        log.info("--------------------")
                        log.info(
                            "No user found for deleted %s.", device["serial"]
                        )
                        log.debug("Error email sent.")

            elapsed_time = time.time() - start_run_time
            log.info("-------")
            log.info("Total time to complete %.2fs.", elapsed_time)

        # Gracefully handle an interrupt
        except KeyboardInterrupt:
            log.debug(
                "\nKeyboard interrupt detected. Logging out & aborting..."
            )

        finally:
            if csrf_token and user_token:
                log.debug("Logging out.")
                if ORG_ID:
                    logout(gather_session, csrf_token, user_token, ORG_ID)

            gather_session.close()
            log.debug("Session closed.\nExiting...")
