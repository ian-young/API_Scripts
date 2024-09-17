"""
Author: Ian Young
Purpose: Will return all devices in a Verkada Command organization.
This is to be imported as a module and not ran directly.
"""

# Import essential libraries
import threading
import time
from os import getenv
from typing import Optional, List

import requests
from dotenv import load_dotenv

from tools import (
    login_and_get_tokens,
    logout,
    log,
    SharedParams,
    create_thread_with_args,
)
from tools.custom_exceptions import APIExceptionHandler
from tools.api_endpoints import (
    AC_URL,
    ALARM_URL,
    VX_URL,
    GC_URL,
    SV_URL,
    BZ_URL,
    GET_CAMERA_DATA,
    GET_SITES,
    set_org_id,
)

load_dotenv()  # Load credentials file

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

ARRAY_LOCK = threading.Lock()


##############################################################################
#################################  Requests  #################################
##############################################################################


def list_cameras(api_key: str, camera_session: requests.Session) -> List[str]:
    """
    Will list all cameras inside of a Verkada organization.

    :param api_key: The API key generated from the organization to target.
    :type api_key: str
    :param camera_session: The request session to use to make the call with.
    :type camera_session: requests.Session
    :return: Returns a list of all camera device IDs found inside of a Verkada
    organization.
    :rtype: list
    """
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    camera_ids = []
    log.debug("Requesting camera data")

    response = camera_session.get(GET_CAMERA_DATA, headers=headers)

    if response.status_code == 400:
        log.warning("No cameras were found in the org.")

    elif response.status_code == 200:
        log.debug("-------")
        log.debug("Camera data retrieved.")

        cameras = response.json()["cameras"]

        log.debug("-------")
        for camera in cameras:
            log.debug("Retrieved %s: %s", camera["name"], camera["camera_id"])
            camera_ids.append(camera["camera_id"])

    else:
        log.error(
            "List cameras endpoint returned with: %s", response.status_code
        )

    return camera_ids


def get_sites(params: SharedParams) -> List[str]:
    """
    Lists all Verkada Guest sites.

    :param params: An instance of SharedParams containing the
        necessary parameters for the deletion process, including session,
        authentication tokens, and organization ID.
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
    site_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting sites.")
        # print(url)
        response = params.session.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Sites JSON retrieved. Parsing and logging.")

        sites = response.json()["sites"]

        log.debug("-------")
        for site in sites:
            log.debug("Retrieved %s: %s", site["siteId"], site["siteName"])
            site_ids.append(site["siteId"])

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        if response.status_code == 403:
            log.warning("No sites found")
        else:
            raise APIExceptionHandler(e, response, "Sites") from e

    return site_ids


def list_ac(params: SharedParams) -> List[str]:
    """
    Lists all access control devices.

    :param params: An instance of SharedParams containing the
        necessary parameters for the deletion process, including session,
        authentication tokens, and organization ID.
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

    access_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting access control devices.")
        response = params.session.post(AC_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Access control JSON retrieved. Parsing and logging.")

        access_devices = response.json()["accessControllers"]

        log.debug("-------")
        for controller in access_devices:
            log.debug(
                "Retrieved controller %s: %s",
                controller["name"],
                controller["deviceId"],
            )

            access_ids.append(controller["deviceId"])

    # Handle exceptions
    except KeyError:
        log.warning("No access controllers found in org.")
    except requests.exceptions.RequestException as e:
        raise APIExceptionHandler(e, response, "Access Control") from e

    return access_ids


def extract_alarm_device(array, key):
    """
    Extracts device IDs from a specified key in an array of alarm devices.

    This function iterates through the devices associated with a given key
    in the input array and collects their device IDs. It logs the
    retrieval of each device's name and ID for debugging purposes.

    Args:
        array (dict): A dictionary containing alarm devices, where the
            specified key maps to a list of devices.
        key (str): The key in the dictionary that corresponds to the list
            of devices to be extracted.

    Returns:
        list: A list of device IDs extracted from the specified key.

    Examples:
        device_ids = extract_alarm_device(alarm_data, "alarms")
    """

    output = []

    log.debug("-------")
    for device in array[key]:
        log.debug(
            "Retrieved %s %s: %s",
            key,
            device["name"],
            device["deviceId"],
        )
        output.append(device["deviceId"])
    return output


def list_alarms(
    params: SharedParams,
) -> tuple[
    List[str], List[str], List[str], List[str], List[str], List[str], List[str]
]:
    """
    Lists all alarm devices.

    :param params: An instance of SharedParams containing the
        necessary parameters for the deletion process, including session,
        authentication tokens, and organization ID.
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

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise APIExceptionHandler(e, response, "Alarms") from e

    return (
        extract_alarm_device(alarm_devices, "doorContactSensor"),
        extract_alarm_device(alarm_devices, "glassBreakSensor"),
        extract_alarm_device(alarm_devices, "hubDevice"),
        extract_alarm_device(alarm_devices, "keypadHub"),
        extract_alarm_device(alarm_devices, "motionSensor"),
        extract_alarm_device(alarm_devices, "panicButton"),
        extract_alarm_device(alarm_devices, "waterSensor"),
    )


def list_viewing_stations(params: SharedParams) -> List[str]:
    """
    Lists all viewing stations.

    :param params: An instance of SharedParams containing the
        necessary parameters for the deletion process, including session,
        authentication tokens, and organization ID.
    :return: An array of archived viewing station device IDs.
    :rtype: list
    """
    body = {"organizationId": params.org_id}

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    vx_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting viewing stations.")
        response = params.session.post(VX_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Viewing station JSON retrieved. Parsing and logging.")

        vx_devices = response.json()["viewingStations"]

        log.debug("-------")
        for vx in vx_devices:
            vx_grid_data = vx["gridData"]
            log.debug(
                "Retrieved viewing station %s: %s",
                vx_grid_data["name"],
                vx["viewingStationId"],
            )
            vx_ids.append(vx["viewingStationId"])

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise APIExceptionHandler(e, response, "Viewing Stations") from e

    return vx_ids


def list_gateways(params: SharedParams) -> List[str]:
    """
    Lists all cellular gateways.

    :param params: An instance of SharedParams containing the
        necessary parameters for the deletion process, including session,
        authentication tokens, and organization ID.
    :return: An array of gateway device IDs.
    :rtype: list
    """
    body = {"organizationId": params.org_id}

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    gc_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting cellular gateways.")
        response = params.session.post(GC_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Cellular gateways JSON retrieved. Parsing and logging.")

        gc_devices = response.json()

        log.debug("-------")
        for gc in gc_devices:
            log.debug(
                "Retrieved cellular gateway %s: %s",
                gc["name"],
                gc["device_id"],
            )
            gc_ids.append(gc["device_id"])

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        if response.status_code == 404:
            log.warning("No gateways found")
        else:
            raise APIExceptionHandler(e, response, "Cellular Gateways") from e

    return gc_ids


def list_sensors(params: SharedParams) -> List[str]:
    """
    Lists all environmental sensors.

    :param params: An instance of SharedParams containing the
        necessary parameters for the deletion process, including session,
        authentication tokens, and organization ID.
    :return: An array of environmental sensor device IDs.
    :rtype: list
    """
    body = {"organizationId": params.org_id}

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    sv_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting environmental sensors.")
        response = params.session.post(SV_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Environmental Sensor JSON retrieved. Parsing and logging.")

        sv_devices = response.json()["sensorDevice"]

        log.debug("-------")
        for sv in sv_devices:
            log.debug(
                "Retrieved Environmental Sensor %s: %s",
                sv["name"],
                sv["deviceId"],
            )
            sv_ids.append(sv["deviceId"])

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise APIExceptionHandler(e, response, "Environmental Sensors") from e

    return sv_ids


def list_horns(params: SharedParams) -> List[str]:
    """
    Lists all BZ horn speakers.

    :param params: An instance of SharedParams containing the
        necessary parameters for the deletion process, including session,
        authentication tokens, and organization ID.
    :return: An array of BZ11 device IDs.
    :rtype: list
    """
    body = {"organizationId": params.org_id}

    headers = {
        "X-CSRF-Token": params.x_verkada_token,
        "X-Verkada-Auth": params.x_verkada_auth,
        "User": params.usr,
    }

    bz_ids = []

    try:
        # Request the JSON archive library
        log.debug("Requesting horn speakers.")
        response = params.session.post(BZ_URL, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Horn speakers JSON retrieved. Parsing and logging.")

        bz_devices = response.json()["garfunkel"]

        log.debug("-------")
        for bz in bz_devices:
            log.debug(
                "Retrieved horn speaker %s: %s", bz["name"], bz["deviceId"]
            )
            bz_ids.append(bz["deviceId"])

        return bz_ids

    # Handle exceptions
    except KeyError:
        log.warning("No BZ11s found in the org.")
        return bz_ids

    except requests.exceptions.RequestException as e:
        raise APIExceptionHandler(e, response, "BZ11 Horn Speakers") from e


def list_desk_stations(params: SharedParams) -> List[str]:
    """
    Lists all desk stations.

    :param params: An instance of SharedParams containing the
        necessary parameters for the deletion process, including session,
        authentication tokens, and organization ID.
    :return: An array of registered desk station apps on iPads.
    :rtype: list
    """
    headers = {
        "x-verkada-organization-id": params.org_id,
        "x-verkada-token": params.x_verkada_token,
        "x-verkada-user-id": params.usr,
    }

    desk_ids = []

    # Request the JSON archive library
    log.debug("Requesting Desk Stations.")
    response = params.session.get(DESK_URL, headers=headers)

    if response.status_code == 403:
        log.warning("No Desk Stations were found in the org.")

    elif response.status_code == 200:
        log.debug("Desk station JSON retrieved. Parsing and logging.")

        desk_stations = response.json()["deskApps"]

        log.debug("-------")
        for ds in desk_stations:
            log.debug(
                "Retrieved Desk Station %s: %s", ds["name"], ds["deviceId"]
            )
            desk_ids.append(ds["deviceId"])

    else:
        log.error(
            "List desk station endpoint returned with: %s",
            str(response.status_code),
        )
    return desk_ids


def list_guest(
    params: SharedParams,
    sites: Optional[List[str]] = None,
) -> tuple[List[str], List[str]]:
    """
    Lists all guest printers and iPads.

    :param params: An instance of SharedParams containing the
        necessary parameters for the deletion process, including session,
        authentication tokens, and organization ID.
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

    ipad_ids, printer_ids = [], []

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
                ipad_ids.append(ipad["deviceId"])
            log.debug("IPads retrieved.")

            log.debug("-------")
            log.debug("Retrieving printers for site %s.", site)
            for printer in guest_devices["printers"]:
                log.debug(
                    "Retrieved guest printer %s: %s",
                    printer["name"],
                    printer["printerId"],
                )
                printer_ids.append(printer["printerId"])
            log.debug("Printers retrieved.")

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise APIExceptionHandler(e, response, "Sites") from e

    return ipad_ids, printer_ids


def list_acls(params: SharedParams) -> tuple[Optional[List[str]], List[str]]:
    """
    Lists all access control levels.

    :param params: An instance of SharedParams containing the
        necessary parameters for the deletion process, including session,
        authentication tokens, and organization ID.
    :return: An array of Verkada access control levels.
    :rtype: list
    """
    headers = {
        "x-verkada-organization-id": params.org_id,
        "x-verkada-token": params.x_verkada_token,
        "x-verkada-user-id": params.usr,
    }

    acl_ids, acls = [], []

    try:
        log.debug("Gathering access control levels.")
        response = params.session.get(ACCESS_LEVELS, headers=headers)

        if response.status_code == 403:
            log.warning("No ACLs were found in this org")

        response.raise_for_status()  # Raise an exception for HTTP errors
        log.debug("Access control levels received.")

        acls = response.json()["schedules"]

        log.debug("-------")
        for acl in acls:
            log.debug("Retrieved %s: %s", acl["name"], acl["scheduleId"])
            acl_ids.append(acl["scheduleId"])
        log.debug("Access levels retrieved.")

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        if response.status_code == 403:
            log.warning("No ACLs found in the org")
        else:
            raise APIExceptionHandler(
                e, response, "Access Control Levels"
            ) from e

    return acls, acl_ids


##############################################################################
##################################  Main  ####################################
##############################################################################


# Check if the script is being imported or ran directly
if __name__ == "__main__":

    with requests.Session() as gather_session:
        start_run_time = time.time()  # Start timing the script
        try:
            # Initialize the user session.
            if USERNAME and PASSWORD and ORG_ID:
                csrf_token, user_token, user_id = login_and_get_tokens(
                    gather_session, USERNAME, PASSWORD, ORG_ID, TOTP
                )

                runtime_params = SharedParams(
                    gather_session, csrf_token, user_token, user_id, ORG_ID
                )

                # Continue if the required information has been received
                if csrf_token and user_token and user_id:
                    # Define the threads with arguments
                    c_thread = create_thread_with_args(
                        list_cameras,
                        [API_KEY, gather_session],
                    )
                    ac_thread = create_thread_with_args(
                        list_ac,
                        [runtime_params],
                    )
                    br_thread = create_thread_with_args(
                        list_alarms,
                        [runtime_params],
                    )
                    vx_thread = create_thread_with_args(
                        list_viewing_stations,
                        [runtime_params],
                    )
                    gc_thread = create_thread_with_args(
                        list_gateways,
                        [runtime_params],
                    )
                    sv_thread = create_thread_with_args(
                        list_sensors,
                        [runtime_params],
                    )
                    bz_thread = create_thread_with_args(
                        list_horns,
                        [runtime_params],
                    )
                    ds_thread = create_thread_with_args(
                        list_desk_stations,
                        [runtime_params],
                    )
                    guest_thread = create_thread_with_args(
                        list_guest,
                        [runtime_params],
                    )
                    acl_thread = create_thread_with_args(
                        list_acls,
                        [runtime_params],
                    )

                    threads = [
                        c_thread,
                        ac_thread,
                        br_thread,
                        vx_thread,
                        gc_thread,
                        sv_thread,
                        bz_thread,
                        ds_thread,
                        guest_thread,
                        acl_thread,
                    ]

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
                    "the authentication process."
                )

            # Calculate the time take to run and post it to the log
            elapsed_time = time.time() - start_run_time
            log.info("-------")
            log.info("Total time to complete %.2fs.", elapsed_time)

        # Gracefully handle an interrupt
        except KeyboardInterrupt:
            log.warning(
                "Keyboard interrupt detected. Logging out & aborting..."
            )

        finally:
            if csrf_token and user_token:
                log.debug("Logging out.")
                if ORG_ID and "csrf_token" in locals():
                    logout(gather_session, csrf_token, user_token, ORG_ID)
            gather_session.close()
            log.debug("Session closed.\nExiting...")
