# Author: Ian Young
# Purpose: Compare users to a pre-defined array of names.
# These names will be "persistent users" which are to remain in Command.
# Any user not marked thusly will be deleted from the org.

import logging, requests, threading, time
from os import getenv
from dotenv import load_dotenv

load_dotenv()

ORG_ID = getenv("lab_id")
API_KEY = getenv("lab_key")

# This will help prevent exceeding the call limit
CALL_COUNT = 0
CALL_COUNT_LOCK = threading.Lock()

# Set logger
log = logging.getLogger()
logging.basicConfig(
    level = logging.INFO,
    format = "%(levelname)s: %(message)s"
    )

# Set the full name for which users are to be persistent
PERSISTENT_USERS = ["Ian Young", "Bruce Banner",
                    "Jane Doe", "Tony Stark", "Ray Raymond", "John Doe"]

# Set URLS
USER_INFO_URL = "https://api.verkada.com/access/v1/access_users"
USER_CONTROL_URL = "https://api.verkada.com/core/v1/user"


def cleanList(list):
    """
    Removes any None values from error codes
    
    :param list: The list to be cleaned.
    :type list: list
    :return: A new list with None values removed.
    :rtype: list
    """
    for value in list:
        if value == None:
            list.remove(value)

    return list


def getUsers(org_id=ORG_ID, api_key=API_KEY):
    """
    Returns JSON-formatted users in a Command org.
    
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: A List of dictionaries of users in an organization.
    :rtype: list
    """
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    params = {
        "org_id": org_id,
    }

    response = requests.get(USER_INFO_URL, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()  # Parse the response

        # Extract as a list
        users = data.get('access_members')
        return users
    else:
        log.critical(
            f"Error with retrieving users.\
Status code {response.status_code}")
        return None


def getIds(users=None):
    """
    Returns an array of all user labels in an organization.
    
    :param users: A list of dictionaries representing users in an
organization. Each dictionary should have 'user' key.
Defaults to None.
    :type users: list, optional
    :return: A list of IDs of the users in an organization.
    :rtype: list
    """
    user_id = []

    for user in users:
        if user.get('user_id'):
            user_id.append(user.get('user_id'))
        else:
            log.error(
                f"There has been an error with user {user.get('full_name')}.")

    return user_id


def getUserId(user=PERSISTENT_USERS, users=None):
    """
    Returns the Verkada ID for a given user.
    
    :param user: The label of a user whose ID is being searched for.
    :type user: str
    :param users: A list of users IDs found inside of an organization.
Each dictionary should have the 'user_id' key. Defaults to None.
    :type users: list, optional
    :return: The user ID of the given user.
    :rtype: str
    """
    user_id = None  # Pre-define

    for name in users:
        if name['full_name'] == user:
            user_id = name['user_id']
            break  # No need to continue running once found

    if user_id:
        return user_id
    else:
        log.error(f"User {user} was not found in the database...")
        return None


def delete_user(user, users, org_id=ORG_ID, api_key=API_KEY):
    """
    Deletes the given user from the organization.

    :param user: The user to be deleted.
    :type user: str
    :param users: A list of PoI IDs found inside of an organization.
    :type users: list
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: None
    :rtype: None
    """
    # Format the URL
    url = USER_CONTROL_URL + "?user_id=" + user + "&org_id=" + org_id

    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    log.info(f"Running for user: {printName(user, users)}")
    
    # Stop if at call limit
    if CALL_COUNT >= 500:
        return
    
    response = requests.delete(url, headers=headers)

    if response.status_code != 200:
        log.error(
            f"An error has occured. Status code {response.status_code}")
        return 2  # Completed unsuccesfully


def purge(delete, users, org_id=ORG_ID, api_key=API_KEY):
    """
    Purges all users that aren't marked as safe/persistent.
    
    :param delete: A list of users to be deleted from the organization.
    :type delete: list
    :param users: A list of users found inside of an organization.
    :type users: list
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: Returns the value of 1 if completed successfully.
    :rtype: int
    """
    global CALL_COUNT

    if not delete:
        log.warning("There's nothing here")
        return

    log.info("Purging...")

    start_time = time.time()
    threads = []
    for user in delete:
        # Stop if at call limit
        if CALL_COUNT >= 500:
            return
        
        thread = threading.Thread(
            target=delete_user, args=(user, users, org_id, api_key)
        )
        thread.start()
        threads.append(thread)

        with CALL_COUNT_LOCK:
            CALL_COUNT += 1

    for thread in threads:
        thread.join()  # Join back to main thread

    end_time = time.time()
    elapsed_time = str(end_time - start_time)

    log.info("Purge complete.")
    log.info(f"Time to complete: {elapsed_time}")
    return 1  # Completed


def printName(to_delete, users):
    """
    Returns the full name of a user with a given ID
    
    :param to_delete: The user ID whose name is being searched for in the
dictionary.
    :type to_delete: str
    :param users: A list of users found inside of an organization.
    :type users: list
    :return: Returns the name of the user searched for. Will return if there
was no name found, as well.
    :rtype: str
    """
    user_name = None  # Pre-define

    for user in users:
        if user.get('user_id') == to_delete:
            user_name = user.get('full_name')
            break  # No need to continue running once found

    if user_name:
        return user_name
    else:
        log.warning(f"User {to_delete} was not found in the database...")
        return "Error finding name"


def run():
    """
    Allows the program to be ran if being imported as a module.
    
    :return: Returns the value 1 if the program completed successfully.
    :rtype: int
    """
    log.info("Retrieving users")
    users = getUsers()
    log.info("Users retrieved.\n")

    # Run if users were found
    if users:
        log.info("Gather IDs")
        all_user_ids = getIds(users)
        all_user_ids = cleanList(all_user_ids)
        log.info("IDs aquired.\n")

        safe_user_ids = []

        # Create the list of safe users
        log.info("Searching for safe users.")
        for user in PERSISTENT_USERS:
            safe_user_ids.append(getUserId(user, users))
        safe_user_ids = cleanList(safe_user_ids)
        log.info("Safe users found.\n")

        # New list that filters users that are safe
        users_to_delete = [
            user for user in all_user_ids if user not in safe_user_ids]

        if users_to_delete:
            purge(users_to_delete, users)
            return 1  # Completed

        else:
            log.info("-------------------------------")
            log.info(
                "The organization has already been purged.\
                      There are no more users to delete.")
            log.info("-------------------------------")

            return 1  # Completed
    else:
        log.warning("No users were found.")

        return 1  # Copmleted


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    run()
