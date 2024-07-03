"""
Author: Ian Young
Purpose: Compare users to a pre-defined array of names.
These names will be "persistent users" which are to remain in Command.
Any user not marked thusly will be deleted from the org.
"""
# Import essential libraries
import logging
import os
import threading
import time

import requests
from dotenv import load_dotenv

load_dotenv()  # Load credentials file

ORG_ID = os.getenv("")
API_KEY = os.getenv("")

# Set logger
log = logging.getLogger()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Set the full name for which users are to be persistent
PERSISTENT_USERS = sorted(
    [
        "Ian Young",
        "Bruce Banner",
        "Jane Doe",
        "Tony Stark",
        "Ray Raymond",
        "John Doe",
    ]
)

# Set URLS
USER_INFO_URL = "https://api.verkada.com/access/v1/access_users"
USER_CONTROL_URL = "https://api.verkada.com/core/v1/user"


##############################################################################
##################################  Misc  ####################################
##############################################################################


class PurgeManager:
    """
    Manages the state of API call count and provides thread-safe methods
    to control and monitor the call limit.

    Attributes:
        call_count (int): The current number of API calls made.
        call_count_lock (threading.Lock): A lock to ensure thread-safe access to call_count.
        call_count_limit (int): The maximum number of API calls allowed.
    """

    def __init__(self, call_count_limit=300):
        """
        Initializes the PurgeManager with a specified call count limit.

        Args:
            call_count_limit (int): The maximum number of API calls allowed.
                                    Defaults to 300.
        """
        self.call_count = 0
        self.call_count_lock = threading.Lock()
        self.call_count_limit = call_count_limit

    def increment_call_count(self):
        """
        Increments the call count by one in a thread-safe manner.

        Returns:
            int: The updated call count after incrementing.
        """
        with self.call_count_lock:
            self.call_count += 1
            return self.call_count

    def should_stop(self):
        """
        Checks if the current call count has reached or exceeded the limit.

        Returns:
            bool: True if the call count has reached or exceeded the limit, False otherwise.
        """
        with self.call_count_lock:
            return self.call_count >= self.call_count_limit

    def reset_call_count(self):
        """
        Resets the call count to zero in a thread-safe manner.
        """
        with self.call_count_lock:
            self.call_count = 0


def clean_list(messy_list):
    """
    Removes any None values from error codes

    :param list: The list to be cleaned.
    :type list: list
    :return: A new list with None values removed.
    :rtype: list
    """
    return [value for value in messy_list if value is not None]


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
        USER_INFO_URL, headers=headers, params=params, timeout=5
    )

    if response.status_code == 200:
        data = response.json()  # Parse the response

        return data.get("access_members")
    else:
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
    # Format the URL
    url = f"{USER_CONTROL_URL}?user_id={user}&org_id={org_id}"

    headers = {"accept": "application/json", "x-api-key": api_key}

    log.info("Running for user: %s", print_name(user, users))

    response = requests.delete(url, headers=headers, timeout=5)

    if response.status_code != 200:
        log.error(
            "An error has occurred. Status code %s", response.status_code
        )
        return 2  # Completed unsuccessfully


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
        return

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
    return 1  # Completed


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


def run():
    """Allows the program to be ran if being imported as a module"""
    log.info("Retrieving users")
    users = get_users()
    log.info("Users retrieved.\n")

    # Run if users were found
    if users:
        handle_people(users)
    else:
        log.warning("No users were found.")

    return 1  # Completed


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


##############################################################################
#  Main  #
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    run()
