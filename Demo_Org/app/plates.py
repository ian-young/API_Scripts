"""
Author: Ian Young
Purpose: Handle plate-related operations.
"""

import threading
import time
from typing import Dict, List, Optional, Union

import requests

from Demo_Org.app.handling import clean_list, flash_led, perform_request
from tools import log, run_thread_with_rate_limit
from tools.api_endpoints import DELETE_LPOI
from .config import (
    ORG_ID,
    API_KEY,
    PERSISTENT_PLATES,
    PERSISTENT_LID,
    MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    BACKOFF,
    RequestConfig,
)
from .handling import GPIO, LPOI_PIN


##############################################################################
############################  All things plates  #############################
##############################################################################


def get_plates(
    org_id: Optional[str] = ORG_ID, api_key: Optional[str] = API_KEY
) -> Optional[List[str]]:
    """
    Returns JSON-formatted plates in a Command org.

    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: A List of dictionaries of license plates in an organization.
    :rtype: list
    """
    headers = {"accept": "application/json", "x-api-key": api_key}

    params = {
        "org_id": org_id,
    }

    response = requests.get(
        DELETE_LPOI, headers=headers, params=params, timeout=5
    )

    if response.status_code == 200:
        data = response.json()  # Parse the response

        # Extract as a list
        plates = data.get("license_plate_of_interest")

        try:
            # Check if the list is iterable
            iter(plates)
        except (TypeError, AttributeError):
            log.error("Plates are not iterable.")
            return None

        return plates

    log.critical(
        "Plate - Error with retrieving plates. Status code %s",
        response.status_code,
    )
    return None


def get_plate_ids(
    plates: Optional[List[Dict[str, str]]] = None
) -> List[Optional[str]]:
    """
    Returns an array of all LPoI labels in an organization.

    :param plates: A list of dictionaries representing LPoIs in an
    organization. Each dictionary should have 'license_plate' key.
    Defaults to None.
    :type plates: list, optional
    :return: A list of IDs of the LPoIs in an organization.
    :rtype: list
    """
    plate_id = []

    if plates:
        for plate in plates:
            if plate.get("license_plate"):
                plate_id.append(plate.get("license_plate"))
            else:
                log.error(
                    "Plate - There has been an error with plate %s.",
                    plate.get("label"),
                )
    else:
        log.error("No list was provided")

    return plate_id


def get_plate_id(
    plate: Optional[Union[str, List[str]]] = PERSISTENT_PLATES,
    plates: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
    """
    Returns the Verkada ID for a given LPoI.

    :param plate: The label of a LPoI whose ID is being searched for.
    :type plate: str
    :param plates: A list of LPoI IDs found inside of an organization.
    Each dictionary should have the 'license_plate' key. Defaults to None.
    :type plates: list, optional
    :return: The plate ID of the given LPoI.
    :rtype: str
    """
    if plates and (
        plate_id := next(
            (
                name["license_plate"]
                for name in plates
                if name["description"] == plate
            ),
            None,
        )
    ):
        return plate_id

    log.error("Plate %s was not found in the database...", plate)

    return None


def delete_plate(
    plate: str,
    plates: List[Dict[str, str]],
    org_id: Optional[str] = ORG_ID,
    api_key: Optional[str] = API_KEY,
):
    """
    Deletes the given plate from the organization.

    :param plate: The plate to be deleted.
    :type plate: str
    :param plates: A list of LPoI IDs found inside of an organization.
    :type plates: list
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: None
    :rtype: None
    """
    local_data = threading.local()
    local_data.RETRY_DELAY = DEFAULT_RETRY_DELAY

    headers = {"accept": "application/json", "x-api-key": api_key}

    log.info("Running for plate: %s", print_plate_name(plate, plates))

    params = {"org_id": org_id, "license_plate": plate}

    config = RequestConfig(
        url=DELETE_LPOI,
        headers=headers,
        params=params,
        print_name=print_plate_name,
        args=(plate, plates),
        backoff=BACKOFF,
    )

    try:
        response = perform_request(config, local_data, MAX_RETRIES)
        response.raise_for_status()

    except requests.HTTPError():
        log.error("An error has ocurred.")


def purge_plates(
    delete: List[Optional[str]],
    plates: List[Dict[str, str]],
    org_id: Optional[str] = ORG_ID,
    api_key: Optional[str] = API_KEY,
):
    """
    Purges all LPoIs that aren't marked as safe/persistent.

    :param delete: A list of LPoIs to be deleted from the organization.
    :type delete: list
    :param plates: A list of LPoIs found inside of an organization.
    :type plates: list
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: Returns the value of 1 if completed successfully.
    :rtype: int
    """
    if not delete:
        log.warning("Plate - There's nothing here")

    local_stop_event = threading.Event()

    if GPIO and LPOI_PIN:
        flash_thread = threading.Thread(
            target=flash_led,
            args=(
                LPOI_PIN,
                local_stop_event,
                0.5,
            ),
        )
        flash_thread.start()

    log.info("Plate - Purging...")

    plate_start_time = time.time()
    threads = []
    for plate in delete:
        # Toss delete function into a new thread
        thread = threading.Thread(
            target=delete_plate,
            args=(
                plate,
                plates,
                org_id,
                api_key,
            ),
        )
        threads.append(thread)  # Add the thread to the pile

    run_thread_with_rate_limit(threads, "LPoI")

    plate_end_time = time.time()
    plate_elapsed_time = plate_end_time - plate_start_time

    log.info("Plate - Purge complete.")
    log.info("Plate - Time to complete: %.2f", plate_elapsed_time)

    if GPIO and LPOI_PIN:
        local_stop_event.set()
        flash_thread.join()


def print_plate_name(to_delete: str, plates: List[Dict[str, str]]) -> str:
    """
        Returns the description of a LPoI with a given ID

        :param to_delete: The person ID whose name is being searched for in the
    dictionary.
        :type to_delete: str
        :param persons: A list of PoIs found inside of an organization.
        :type persons: list
        :return: Returns the name of the person searched for. Will return if there
    was no name found, as well.
        :rtype: str
    """
    plate_name = next(
        (
            plate.get("description")
            for plate in plates
            if plate.get("license_plate") == to_delete
        ),
        None,
    )
    return plate_name or "No name provided"


def run_plates():
    """
    Allows the program to be ran if being imported as a module.

    :return: Returns the value 1 if the program completed successfully.
    :rtype: int
    """
    log.info("Retrieving plates")
    plates = get_plates()
    log.info("Plates retrieved.")

    if plates := sorted(plates, key=lambda x: x["license_plate"]):
        handle_plates(plates)
    else:
        log.info("No plates were found.")


def handle_plates(plates: List[Dict[str, str]]):
    """
    Handle the processing of plates by gathering IDs, searching for safe
    plates, and deleting plates if needed.

    Args:
        plates: The list of plates to handle.

    Returns:
        None
    """
    log.info("Plate - Gather IDs")
    all_plate_ids = get_plate_ids(plates)
    all_plate_ids = clean_list(all_plate_ids)
    log.info("Plate - IDs acquired.")

    log.info("Searching for safe plates.")
    safe_plate_ids = [
        get_plate_id(plate, plates) for plate in PERSISTENT_PLATES
    ]
    safe_plate_ids = clean_list(safe_plate_ids)

    if PERSISTENT_LID:
        for plate in PERSISTENT_LID:
            safe_plate_ids.append(plate)
    log.info("Safe plates found.")

    if plates_to_delete := [
        plate for plate in all_plate_ids if plate not in safe_plate_ids
    ]:
        purge_plates(plates_to_delete, plates)
    else:
        log.info(
            "The organization has already been purged.\
There are no more plates to delete."
        )
