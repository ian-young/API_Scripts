"""
Author: Ian Young
Purpose: Reset a Verkada Command organization for use at VCE. An API key and
valid user credentials are needed to run this script. Please use EXTREME
caution when running because this will delete all devices from an org
without any additional warnings.
"""

# Import essential libraries
import threading
import time
from dataclasses import dataclass
from os import getenv
from typing import Optional, Dict, List, Any

import requests
from colorama import Fore, Style, init
from dotenv import load_dotenv

from v_certified_engineer import gather_devices
from tools import (
    login_and_get_tokens,
    logout,
    custom_exceptions,
    log,
    run_thread_with_rate_limit,
    SharedParams,
)

init(autoreset=True)  # Initialize colorized output

load_dotenv()  # Load credentials file

# Set final, global credential variables
API_KEY = getenv("")
USERNAME = getenv("")
PASSWORD = getenv("")
ORG_ID = getenv("")

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
###################################  Misc  ###################################
##############################################################################


@dataclass
class DeviceDeletionParams:
    """
    Data class that holds parameters for device deletion operations.

    This class encapsulates the necessary parameters required to delete
    devices from the Verkada API. It provides a structured way to manage
    the information needed for the deletion process.

    Attributes:
        devices (List[str]): A list of device IDs to be deleted.
        device_type (str): The type of the devices being deleted.
        url (str): The API endpoint URL for deleting the devices.
        headers (dict): The headers to be included in the API request.
        alarm_session (requests.Session): The session used for making
            the API calls.
        org_id (Optional[str]): The organization ID for the targeted
            Verkada organization.
    """

    devices: List[str]
    device_type: str
    url: str
    headers: dict
    alarm_session: requests.Session
    org_id: Optional[str]


@dataclass
class DeleteParams:
    """
    Data class that holds parameters for device deletion requests.

    This class organizes the essential parameters needed to perform a
    deletion request for a specific device. It provides a clear structure
    for managing the information required for the API call.

    Attributes:
        url (str): The API endpoint URL for the deletion request.
        device_id (str): The ID of the device to be deleted.
        headers (dict): The headers to be included in the API request.
        params (dict): Additional parameters for the API request.
        session (requests.Session): The session used for making the API
            calls.
    """

    url: str
    device_id: str
    headers: dict
    params: dict
    session: requests.Session


##############################################################################
################################  Requests  ##################################
##############################################################################


def delete_cameras(params: SharedParams):
    """
    Deletes cameras from the Verkada organization.

    This function retrieves a list of cameras and sends requests to delete
    each one from the Verkada API. It handles potential request exceptions
    and logs the outcome of the deletion process.

    Args:
        params (SharedParams): An instance of SharedParams containing the
            necessary parameters for the deletion process, including
            session, authentication tokens, and organization ID.

    Returns:
        None

    Raises:
        custom_exceptions.APIExceptionHandler: If there is an error during
            the deletion process.

    Examples:
        delete_cameras(shared_params_instance)
    """

    headers = {
        "x-verkada-organization-id": params.org_id,
        "x-verkada-token": params.x_verkada_token,
        "x-verkada-user-id": params.usr,
    }

    try:
        log.debug("Requesting cameras.")
        if API_KEY is not None:
            if cameras := gather_devices.list_cameras(API_KEY, params.session):
                for camera in cameras:
                    body = {"cameraId": camera}

                    response = params.session.post(
                        CAMERA_DECOM, headers=headers, json=body
                    )
                    response.raise_for_status()

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


def delete_alarm_device(params: DeviceDeletionParams):
    """
    Deletes specified devices from the Verkada Command.

    Args:
        params (DeviceDeletionParams): An instance of
            DeviceDeletionParams containing the parameters.

    Raises:
        custom_exceptions.APIExceptionHandler: If there is an error during
            the deletion process.
    """
    for device in params.devices:
        try:
            response = params.alarm_session.post(
                params.url,
                headers=params.headers,
                json={
                    "deviceId": device,
                    "deviceType": params.device_type,
                    "organizationId": params.org_id,
                },
            )
            response.raise_for_status()
            log.debug("Deleted %s: %s", params.device_type, device)
        except requests.exceptions.RequestException as e:
            raise custom_exceptions.APIExceptionHandler(
                e, response, f"{params.device_type} deletion failed"
            ) from e


def process_keypads(
    device_ids: List[str],
    headers: dict,
    alarm_session: requests.Session,
    org_id: Optional[str],
):
    """
    Processes the deletion of keypads from the Verkada Command.

    Args:
        device_ids (List[str]): A list of device IDs for the keypads to be
            deleted.
        headers (dict): HTTP headers for the request.
        alarm_session (requests.Session): The session to use for making
            requests.
        org_id (Optional[str]): The organization ID.

    Raises:
        custom_exceptions.APIExceptionHandler: If there is an error during the
            deletion process.
    """
    for device_id in device_ids:
        try:
            response = alarm_session.post(
                APANEL_DECOM,
                headers=headers,
                json={"deviceId": device_id, "organizationId": org_id},
            )
            response.raise_for_status()
            log.debug("Keypad deleted: %s", device_id)
        except requests.exceptions.HTTPError as e:
            if response.status_code != 400:
                raise custom_exceptions.APIExceptionHandler(
                    e, response, "Keypad deletion failed"
                ) from e
            response = alarm_session.post(
                AKEYPADS_DECOM,
                headers=headers,
                json={"deviceId": device_id, "organizationId": org_id},
            )
            if response.status_code == 200:
                log.debug("Keypad deleted successfully: %s", device_id)
            else:
                log.warning(
                    "Could not delete keypad: %s, Status code: %s",
                    device_id,
                    response.status_code,
                )


def create_and_run_threads(
    devices: dict,
    headers: dict,
    alarm_session: requests.Session,
    org_id: Optional[str],
):
    """
    Creates and runs threads for deleting various types of devices.

    Args:
        devices (dict): A dictionary where keys are device types and
            values are tuples containing the API endpoint URL and a list of
            device IDs to be deleted.
        headers (dict): HTTP headers for the request.
        alarm_session (requests.Session): The session to use for making
            requests.
        org_id (Optional[str]): The organization ID.

    Returns:
        None
    """
    alarm_threads = []

    # Add threads for each device type
    for device_type, (url, ids) in devices.items():
        if ids:
            params = DeviceDeletionParams(
                devices=ids,
                device_type=device_type,
                url=url,
                headers=headers,
                alarm_session=alarm_session,
                org_id=org_id,
            )
            alarm_threads.append(
                threading.Thread(target=delete_alarm_device, args=(params,))
            )

    if keypad_ids := devices.get("keypad", [None, []])[1]:
        alarm_threads.append(
            threading.Thread(
                target=process_keypads,
                args=(keypad_ids, headers, alarm_session, org_id),
            )
        )

    # Start and join all threads
    for thread in alarm_threads:
        thread.start()
    for thread in alarm_threads:
        thread.join()

    # Log the result
    log.info(
        "Alarm sensors deleted."
        if alarm_threads
        else "No alarm sensors were received."
    )


def delete_sensors(params: SharedParams):
    """
    Deletes all alarm devices from a Verkada organization.

    Args:
        params (SharedParams): An instance of SharedParams containing the
            necessary parameters for the deletion process, including
            session, authentication tokens, and organization ID.

    Raises:
        custom_exceptions.APIExceptionHandler: If there is an error during
            the deletion process.

    Examples:
        delete_sensors("token", "auth", "user_id", session, "org_id")
    """
    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
        "Content-Type": "application/json",
    }

    # Request all alarm sensors
    log.debug("Requesting alarm sensors.")
    dcs, gbs, hub, ms, pb, ws, wr = gather_devices.list_alarms(params)

    # Prepare device data for threads
    devices = {
        "doorContactSensor": (ASENSORS_DECOM, dcs),
        "glassBreakSensor": (ASENSORS_DECOM, gbs),
        "motionSensor": (ASENSORS_DECOM, ms),
        "panicButton": (ASENSORS_DECOM, pb),
        "waterSensor": (ASENSORS_DECOM, ws),
        "wirelessRelay": (ASENSORS_DECOM, wr),
        "keypad": (APANEL_DECOM, hub) if hub else (None, []),
    }

    create_and_run_threads(
        {key: value for key, value in devices.items() if value[1]},
        headers,
        params.session,
        params.org_id,
    )


def delete_panels(params: SharedParams):
    """
    Deletes access control panels from the Verkada organization.

    This function retrieves a list of access control panels and sends
    requests to delete each one from the Verkada API. It handles potential
    request exceptions and logs the outcome of the deletion process,
    including special handling for intercoms if a specific error occurs.

    Args:
        params (SharedParams): An instance of SharedParams containing the
            necessary parameters for the deletion process, including session,
            authentication tokens, and organization ID.

    Returns:
        None

    Raises:
        custom_exceptions.APIExceptionHandler: If there is an error during
            the deletion process.

    Examples:
        delete_panels(shared_params_instance)
    """

    exempt: List[str] = []

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting Access control panels.")
        if panels := gather_devices.list_ac(params):
            for panel in panels:
                if panel not in exempt:
                    log.debug("Running for access control panel: %s", panel)

                    data = {"deviceId": panel}

                    response = params.session.post(
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
            # Try as intercom
            delete_intercom(params, panel)
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


def delete_intercom(params: SharedParams, device_id: str):
    """
    Deletes a specified intercom from the Verkada organization.

    This function sends a request to delete a specific intercom identified
    by its device ID from the Verkada API. It handles potential request
    exceptions and logs the outcome of the deletion process.

    Args:
        params (SharedParams): An instance of SharedParams containing the
            necessary parameters for the deletion process, including session,
            authentication tokens, and organization ID.
        device_id (str): The ID of the intercom to be deleted.

    Returns:
        None

    Raises:
        custom_exceptions.APIExceptionHandler: If there is an error during
            the deletion process.

    Examples:
        delete_intercom(shared_params_instance, "intercom_id")
    """

    headers = {
        "x-verkada-organization-id": params.org_id,
        "x-verkada-token": params.x_verkada_token,
        "x-verkada-user-id": params.usr,
    }

    try:
        url = DESK_DECOM + device_id + SHARD

        log.debug("Running for intercom: %s", device_id)

        response = params.session.delete(url, headers=headers)
        response.raise_for_status()  # Raise for HTTP errors

        log.info("%sIntercom deleted.%s", Fore.GREEN, Style.RESET_ALL)

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        ptype = "Intercom"
        raise custom_exceptions.APIExceptionHandler(e, response, ptype) from e


def delete_environmental(params: SharedParams):
    """
    Deletes environmental sensors from the Verkada organization.

    This function retrieves a list of environmental sensors and sends
    requests to delete each one from the Verkada API. It handles potential
    request exceptions and logs the outcome of the deletion process.

    Args:
        params (SharedParams): An instance of SharedParams containing the
            necessary parameters for the deletion process, including
            session, authentication tokens, and organization ID.

    Returns:
        None

    Raises:
        custom_exceptions.APIExceptionHandler: If there is an error during
            the deletion process.

    Examples:
        delete_environmental(shared_params_instance)
    """

    param = {"organizationId": params.org_id}

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Requesting environmental sensors.")
        if sv_ids := gather_devices.list_sensors(params):
            for sensor in sv_ids:
                data = {"deviceId": sensor}

                log.info("Running for environmental sensor %s", sensor)

                response = params.session.post(
                    ENVIRONMENTAL_DECOM,
                    json=data,
                    headers=headers,
                    params=param,
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


def delete_ipad(params: DeleteParams):
    """
    Deletes an iPad from Verkada.

    Args:
        params (DeleteParams): Parameters needed for the deletion request.

    Raises:
        requests.exceptions.RequestException: If there is an HTTP error
            during the request.
    """
    try:
        url = f"{params.url}{params.device_id}"
        response = params.session.delete(
            url, headers=params.headers, params=params.params
        )
        response.raise_for_status()
        log.info("Deleted iPad %s successfully.", params.device_id)
    except requests.exceptions.RequestException as e:
        log.error("Error deleting iPad %s: %s", params.device_id, e)
        raise


def delete_printer(params: DeleteParams):
    """
    Deletes a printer from Verkada.

    Args:
        params (DeleteParams): Parameters needed for the deletion
            request.

    Raises:
        requests.exceptions.RequestException: If there is an HTTP error
            during the request.
    """
    try:
        url = f"{params.url}{params.device_id}"
        response = params.session.delete(
            url, headers=params.headers, params=params.params
        )
        response.raise_for_status()
        log.info("Deleted printer %s successfully.", params.device_id)
    except requests.exceptions.RequestException as e:
        log.error("Error deleting printer %s: %s", params.device_id, e)
        raise


def delete_guest(params: SharedParams):
    """
    Deletes guest devices, specifically iPads and printers, from the
    Verkada organization.

    This function retrieves a list of sites and guest devices, then sends
    requests to delete each iPad and printer associated with those sites.
    It handles potential request exceptions and logs the outcome of the
    deletion process for each site.

    Args:
        params (SharedParams): An instance of SharedParams containing the
            necessary parameters for the deletion process, including session,
            authentication tokens, and organization ID.

    Returns:
        None

    Raises:
        custom_exceptions.APIExceptionHandler: If there is an error during
            the deletion process.

    Examples:
        delete_guest(shared_params_instance)
    """

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }
    param = {"organizationId": params.org_id}

    try:
        log.debug("Initiating site request.")
        sites = gather_devices.get_sites(params)

        log.debug("Initiating Guest requests.")
        ipad_ids, printer_ids = gather_devices.list_guest(params, sites)

        for site in sites:
            if any(ipad_ids):  # Check if there are iPads to delete
                for ipad in filter(
                    None, ipad_ids
                ):  # Filter out None or empty values
                    delete_ipad(
                        DeleteParams(
                            url=GUEST_IPADS_DECOM,
                            device_id=ipad,
                            headers=headers,
                            params=param,
                            session=params.session,
                        )
                    )
                log.info("iPads deleted for site %s", site)

            if any(printer_ids):  # Check if there are printers to delete
                for printer in filter(
                    None, printer_ids
                ):  # Filter out None or empty values
                    delete_printer(
                        DeleteParams(
                            url=GUEST_PRINTER_DECOM,
                            device_id=printer,
                            headers=headers,
                            params=param,
                            session=params.session,
                        )
                    )
                log.info("Printers deleted for site %s", site)

            if not any(ipad_ids) and not any(
                printer_ids
            ):  # Check if both are empty
                log.warning(
                    "No Guest devices were received for site %s.", site
                )

    except requests.exceptions.RequestException as e:
        raise custom_exceptions.APIExceptionHandler(e, None, "Guest") from e


def delete_acls(params: SharedParams):
    """
    Deletes access control levels (ACLs) from the Verkada organization.

    This function retrieves a list of access control levels and sends
    requests to delete each one by marking it as deleted. It handles
    potential request exceptions and logs the outcome of the deletion
    process.

    Args:
        params (SharedParams): An instance of SharedParams containing the
            necessary parameters for the deletion process, including
            session, authentication tokens, and organization ID.

    Returns:
        None

    Raises:
        custom_exceptions.APIExceptionHandler: If there is an error during
            the deletion process.

    Examples:
        delete_acls(shared_params_instance)
    """

    def find_schedule_by_id(
        schedule_id, schedules
    ) -> Optional[Dict[str, Any]]:
        for schedule in schedules:
            if schedule["scheduleId"] == schedule_id:
                return schedule
        return None

    headers = {
        "x-verkada-organization-id": params.org_id,
        "x-verkada-token": params.x_verkada_token,
        "x-verkada-user-id": params.usr,
    }

    try:
        # Request the JSON archive library
        log.debug("Initiating request for access control levels.")
        acls, acl_ids = gather_devices.list_acls(params)

        if acls is not None and acl_ids is not None:
            for acl in acl_ids:
                if schedule := find_schedule_by_id(acl, acls):
                    log.info("Running for access control level %s", acl)
                    schedule["deleted"] = True
                    data = {"sitesEnabled": True, "schedules": [schedule]}

                    response = params.session.put(
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


def delete_desk_station(params: SharedParams):
    """
    Deletes desk stations from the Verkada organization.

    This function retrieves a list of desk stations and sends requests to
    delete each one from the Verkada API. It handles potential request
    exceptions and logs the outcome of the deletion process.

    Args:
        params (SharedParams): An instance of SharedParams containing the
            necessary parameters for the deletion process, including
            session, authentication tokens, and organization ID.

    Returns:
        None

    Raises:
        custom_exceptions.APIExceptionHandler: If there is an error during
            the deletion process.

    Examples:
        delete_desk_station(shared_params_instance)
    """

    headers = {
        "x-verkada-organization-id": params.org_id,
        "x-verkada-token": params.x_verkada_token,
        "x-verkada-user-id": params.usr,
    }

    try:
        # Request the JSON library for Desk Station
        log.debug("Initiating Desk Station requests.")
        if ds_ids := gather_devices.list_desk_stations(params):
            for desk_station in ds_ids:
                url = DESK_DECOM + desk_station + SHARD

                log.debug(
                    "%sRunning for Desk Station: %s%s",
                    Fore.GREEN,
                    desk_station,
                    Style.RESET_ALL,
                )

                response = params.session.delete(url, headers=headers)
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
    with requests.Session() as delete_session:
        try:
            # Initialize the user session.
            if USERNAME and PASSWORD and ORG_ID:
                csrf_token, user_token, user_id = login_and_get_tokens(
                    delete_session, USERNAME, PASSWORD, ORG_ID
                )

                # Continue if the required information has been received
                if csrf_token and user_token and user_id:
                    runtime_params = SharedParams(
                        delete_session, csrf_token, user_token, user_id, ORG_ID
                    )

                    # Place each element in their own thread to speed up runtime
                    camera_thread = threading.Thread(
                        target=delete_cameras,
                        args=(runtime_params,),
                    )

                    alarm_thread = threading.Thread(
                        target=delete_sensors,
                        args=(runtime_params,),
                    )

                    ac_thread = threading.Thread(
                        target=delete_panels,
                        args=(runtime_params,),
                    )

                    sv_thread = threading.Thread(
                        target=delete_environmental,
                        args=(runtime_params,),
                    )

                    guest_thread = threading.Thread(
                        target=delete_guest,
                        args=(runtime_params,),
                    )

                    acl_thread = threading.Thread(
                        target=delete_acls,
                        args=(runtime_params,),
                    )

                    desk_thread = threading.Thread(
                        target=delete_desk_station,
                        args=(runtime_params,),
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
                    run_thread_with_rate_limit(threads, "Deleting Devices")

            # Handles when the required credentials were not received
            else:
                log.critical(
                    "%sNo credentials were provided during authentication %s",
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
            if csrf_token and user_token and ORG_ID:
                logout(delete_session, csrf_token, user_token, ORG_ID)
            delete_session.close()
            log.debug("Session closed.\nExiting...")
