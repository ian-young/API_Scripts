"""
Author: Ian Young
Purpose: Handle people-related operations.
"""

import threading
import time
from typing import Dict, List, Optional, Union

import requests

from Demo_Org.app.handling import clean_list, flash_led, perform_request
from tools import log
from tools.api_endpoints import DELETE_POI
from tools.rate_limit import run_thread_with_rate_limit
from .config import (
    ORG_ID,
    API_KEY,
    PERSISTENT_PERSONS,
    PERSISTENT_PID,
    MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    BACKOFF,
    RequestConfig,
)
from .handling import GPIO, POI_PIN

##############################################################################
############################  All things people  #############################
##############################################################################


def get_people(
    org_id: Optional[str] = ORG_ID, api_key: Optional[str] = API_KEY
) -> Optional[List[str]]:
    """
    Returns JSON-formatted persons in a Command org.

    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: A List of dictionaries of people in an organization.
    :rtype: list
    """
    headers = {"accept": "application/json", "x-api-key": api_key}

    params = {
        "org_id": org_id,
    }

    response = requests.get(
        DELETE_POI, headers=headers, params=params, timeout=5
    )

    if response.status_code == 200:
        data = response.json()  # Parse the response

        # Extract as a list
        persons = data.get("persons_of_interest")

        try:
            iter(persons)
        except (TypeError, AttributeError):
            log.error("People are not iterable.")
            return None

        return persons

    log.critical(
        "Person - Error with retrieving persons. Status code %s",
        {response.status_code},
    )
    return None


def get_people_ids(
    persons: Optional[List[Dict[str, str]]] = None
) -> List[Optional[str]]:
    """
    Returns an array of all PoI labels in an organization.

    :param persons: A list of dictionaries representing PoIs in an
    organization. Each dictionary should have 'person_id' key.
    Defaults to None.
    :type persons: list, optional
    :return: A list of IDs of the PoIs in an organization.
    :rtype: list
    """
    person_id = []
    if persons:
        for person in persons:
            if person.get("person_id"):
                person_id.append(person.get("person_id"))
            else:
                log.error(
                    "There has been an error with person %s.",
                    person.get("label"),
                )
    else:
        log.error("No list was provided.")

    return person_id


def get_person_id(
    person: Union[str, List[str]] = PERSISTENT_PERSONS,
    persons: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
    """
        Returns the Verkada ID for a given PoI.

        :param person: The label of a PoI whose ID is being searched for.
        :type person: str
        :param persons: A list of PoI IDs found inside of an organization.
    Each dictionary should have the 'person_id' key. Defaults to None.
        :type persons: list, optional
        :return: The person ID of the given PoI.
        :rtype: str
    """
    if persons:
        if person_id := next(
            (name["person_id"] for name in persons if name["label"] == person),
            None,
        ):
            return person_id
        log.warning("Person %s was not found in the database...", person)

    else:
        log.error("No list was provided.")

    return None


def delete_person(
    person: str,
    persons: List[Dict[str, str]],
    org_id: Optional[str] = ORG_ID,
    api_key: Optional[str] = API_KEY,
):
    """
    Deletes the given person from the organization.

    :param person: The person to be deleted.
    :type person: str
    :param persons: A list of PoI IDs found inside of an organization.
    :type persons: list
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

    log.info("Running for person: %s", print_person_name(person, persons))

    params = {"org_id": org_id, "person_id": person}

    config = RequestConfig(
        url=DELETE_POI,
        headers=headers,
        params=params,
        print_name=print_person_name,
        args=(person, persons),
        backoff=BACKOFF,
    )

    try:
        response = perform_request(config, local_data, MAX_RETRIES)
        response.raise_for_status()

    except requests.HTTPError():
        log.error("An error has ocurred.")


def purge_people(
    delete: List[Optional[str]],
    persons: List[Dict[str, str]],
    org_id: Optional[str] = ORG_ID,
    api_key: Optional[str] = API_KEY,
):
    """
    Purges all PoIs that aren't marked as safe/persistent.

    :param delete: A list of PoIs to be deleted from the organization.
    :type delete: list
    :param persons: A list of PoIs found inside of an organization.
    :type persons: list
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: Returns the value of 1 if completed successfully.
    :rtype: int
    """
    if not delete:
        log.warning("Person - There's nothing here")

    local_stop_event = threading.Event()

    if GPIO and POI_PIN:
        flash_thread = threading.Thread(
            target=flash_led,
            args=(
                POI_PIN,
                local_stop_event,
                0.5,
            ),
        )
        flash_thread.start()

    log.info("Person - Purging...")

    person_start_time = time.time()
    threads = []
    for person in delete:
        # Toss delete function into a new thread
        thread = threading.Thread(
            target=delete_person,
            args=(
                person,
                persons,
                org_id,
                api_key,
            ),
        )
        threads.append(thread)  # Add the thread to the pile

    run_thread_with_rate_limit(threads, "PoI")

    person_end_time = time.time()
    person_elapsed_time = person_end_time - person_start_time

    log.info("Person - Purge complete.")
    log.info("Person - Time to complete: %.2f", person_elapsed_time)

    if GPIO and POI_PIN:
        local_stop_event.set()
        flash_thread.join()


def print_person_name(to_delete: str, persons: List[Dict[str, str]]) -> str:
    """
    Returns the label of a PoI with a given ID

    :param to_delete: The person ID whose name is being searched for in the
    dictionary.
    :type to_delete: str
    :param persons: A list of PoIs found inside of an organization.
    :type persons: list
    :return: Returns the name of the person searched for. Will return if there
    was no name found, as well.
    :rtype: str
    """
    person_name = next(
        (
            person.get("label")
            for person in persons
            if person.get("person_id") == to_delete
        ),
        None,
    )
    return person_name or "No name provided"


def run_people():
    """
    Allows the program to be ran if being imported as a module.

    :return: Returns the value 1 if the program completed successfully.
    :rtype: int
    """
    log.info("Retrieving persons")
    persons = get_people()
    log.info("persons retrieved.")

    if persons := sorted(persons, key=lambda x: x["person_id"]):
        handle_people(persons)
    else:
        log.warning("No persons were found.")


def handle_people(persons: List[Dict[str, str]]):
    """
    Handle the processing of people by gathering IDs, searching for
    safe people, and deleting people if needed.

    Args:
        persons: The list of people to handle.

    Returns:
        None
    """
    log.info("Person - Gather IDs")
    all_person_ids = get_people_ids(persons)
    all_person_ids = clean_list(all_person_ids)
    log.info("Person - IDs acquired.")

    log.info("Searching for safe persons.")
    safe_person_ids = [
        get_person_id(person, persons) for person in PERSISTENT_PERSONS
    ]
    safe_person_ids = clean_list(safe_person_ids)

    if PERSISTENT_PID:
        for person in PERSISTENT_PID:
            safe_person_ids.append(person)
    log.info("Safe persons found.")

    if persons_to_delete := [
        person for person in all_person_ids if person not in safe_person_ids
    ]:
        purge_people(persons_to_delete, persons)
    else:
        log.info(
            "Person - The organization has already been purged.\
There are no more persons to delete."
        )
