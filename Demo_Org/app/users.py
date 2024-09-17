"""
Author: Ian Young
Purpose: Handle user-related operations
"""

import threading
import time

import requests

from app import PurgeManager
from tools import log
from tools.api_endpoints import DELETE_USER, GET_ALL_AC_USRS

from .config import (
    API_KEY,
    ORG_ID,
    PERSISTENT_USERS,
    BACKOFF,
    MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
)
from .handling import clean_list, RequestConfig, perform_request


##############################################################################
############################  All things Users  ##############################
##############################################################################


def get_users(org_id=ORG_ID, api_key=API_KEY):
    """
    Returns JSON-formatted users in a Command org

    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: A List of dictionaries of users in an organization.
    :rtype: list
    """
    headers = {"accept": "application/json", "x-api-key": api_key}

    params = {
        "org_id": org_id,
    }

    response = requests.get(
        GET_ALL_AC_USRS, headers=headers, params=params, timeout=5
    )

    if response.status_code == 200:
        data = response.json()  # Parse the response

        return data.get("access_members")

    log.critical(
        "Error with retrieving users. Status code %s", response.status_code
    )
    return None


def get_ids(users=None):
    """
    Returns an array of all user IDs in an organization

    :param users: A list of dictionaries representing PoIs in an
    organization. Each dictionary should have 'person_id' key.
    Defaults to None.
    :type users: list, optional
    :return: A list of IDs of the users in an organization.
    :rtype: list
    """
    user_id = []

    for user in users:
        if user.get("user_id"):
            user_id.append(user.get("user_id"))
        else:
            log.error(
                "There has been an error with user %s.", user.get("full_name")
            )

    return user_id


def get_user_id(user=PERSISTENT_USERS, users=None):
    """
    Returns the Verkada user_id for a given user

    :param user: The name of the user whose ID is being searched for.
    :type user: str
    :param users: A list of PoI IDs found inside of an organization.
    Each dictionary should have the 'user_id' key. Defaults to None.
    :type users: list, optional
    :return: The user ID of the given user.
    :rtype: str
    """
    if user_id := next(
        (name["user_id"] for name in users if name["full_name"] == user), None
    ):
        return user_id
    log.error("User %s was not found in the database...", user)
    return None


def delete_user(user, users, org_id=ORG_ID, api_key=API_KEY):
    """
    Deletes the given user

    :param user: The user to be deleted.
    :type user: str
    :param users: A list of user IDs found inside of an organization.
    :type users: list
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: None
    :rtype: None
    """
    local_data = threading.local()
    local_data.RETRY_DELAY = DEFAULT_RETRY_DELAY
    # Format the URL
    url = f"{DELETE_USER}?user_id={user}&org_id={org_id}"

    headers = {"accept": "application/json", "x-api-key": api_key}

    log.info("Running for user: %s", print_name(user, users))

    config = RequestConfig(
        url=url,
        headers=headers,
        params={},
        print_name=print_name,
        args=(user, users),
        backoff=BACKOFF,
    )

    try:
        response = perform_request(config, local_data, MAX_RETRIES)
        response.raise_for_status()

    except requests.HTTPError():
        log.error("An error has ocurred.")


def purge(delete, users, manager, org_id=ORG_ID, api_key=API_KEY):
    """
    Purges all users that aren't marked as safe/persistent

    :param delete: A list of users to be deleted from the organization.
    :type delete: list
    :param persons: A list of users found inside of an organization.
    :type persons: list
    :param manager: PurgeManager instance to manage call count and thread
    safety.
    :type manager: PurgeManager
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: Returns the value of 1 if completed successfully.
    :rtype: int
    """
    if not delete:
        log.warning("There's nothing here")

    log.info("Purging...")

    start_time = time.time()
    threads = []

    for user in delete:
        while manager.should_stop():
            log.info("Call limit reached, waiting for 1 second.")
            time.sleep(1)
            manager.reset_call_count()

        thread = threading.Thread(
            target=delete_user,
            args=(
                user,
                users,
                org_id,
                api_key,
            ),
        )
        thread.start()
        threads.append(thread)

        manager.increment_call_count()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    end_time = time.time()
    elapsed_time = str(end_time - start_time)

    log.info("Purge complete.")
    log.info("Time to complete: %.2fs.", elapsed_time)


def print_name(to_delete, users):
    """
    Returns the full name with a given ID

    :param to_delete: The list of users to delete.
    :type to_delete: list
    :param users: A complete list of all Command users.
    :type users: list
    :return: The name of the user
    :rtype: str
    """
    if user_name := next(
        (
            user.get("full_name")
            for user in users
            if user.get("user_id") == to_delete
        ),
        None,
    ):
        return user_name
    log.warning("User %s was not found in the database...", to_delete)
    return "Error finding name"


def run_users():
    """Allows the program to be ran if being imported as a module"""
    log.info("Retrieving users")
    users = get_users()
    log.info("Users retrieved.\n")

    # Run if users were found
    if users:
        handle_people(users)
    else:
        log.warning("No users were found.")


def handle_people(users):
    """
    Handle the processing of users by gathering IDs, searching for safe
    users, and deleting users if needed.

    Args:
        users: The list of users to handle.

    Returns:
        None
    """
    log.info("Gather IDs")
    all_user_ids = get_ids(users)
    all_user_ids = clean_list(all_user_ids)
    log.info("IDs acquired.\n")

    # Create the list of safe users
    log.info("Searching for safe users.")
    safe_user_ids = [get_user_id(user, users) for user in PERSISTENT_USERS]
    safe_user_ids = clean_list(safe_user_ids)
    log.info("Safe users found.\n")

    if users_to_delete := [
        user for user in all_user_ids if user not in safe_user_ids
    ]:
        purge_manager = PurgeManager(call_count_limit=300)
        purge(users_to_delete, users, purge_manager)
    else:
        log.info("-------------------------------")
        log.info(
            "The organization has already been purged."
            "There are no more users to delete."
        )
        log.info("-------------------------------")
