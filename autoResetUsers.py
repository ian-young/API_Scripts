# Author: Ian Young
# Purpose: Compare users to a pre-defined array of names.
# These names will be "persistent users" which are to remain in Command.
# Any user not marked thusly will be deleted from the org.

import requests

ORG_ID = ""
API_KEY = ""

# Set the full name for which users are to be persistent
PERSISTENT_USERS = ["Ian Young", "Bruce Banner",
                    "Jane Doe", "Tony Stark", "Ray Raymond", "John Doe"]

# Set URLS
USER_INFO_URL = "https://api.verkada.com/access/v1/access_users"
USER_CONTROL_URL = "https://api.verkada.com/core/v1/user"


def cleanList(list):
    """Removes any None values from error codes"""
    for value in list:
        if value == None:
            list.remove(value)

    return list


def getUsers(org_id=ORG_ID, api_key=API_KEY):
    """Returns JSON-formatted users in a Command org"""
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
        print(
            f"Error with retrieving users.\
Status code {response.status_code}")
        return None


def getIds(users=None):
    """Returns an array of all user IDs in an organization"""
    user_id = []

    for user in users:
        if user.get('user_id'):
            user_id.append(user.get('user_id'))
        else:
            print(
                f"There has been an error with user {user.get('full_name')}.")

    return user_id


def getUserId(user=PERSISTENT_USERS, users=None):
    """Returns the Verkada user_id for a given user"""
    user_id = None  # Pre-define

    for name in users:
        if name['full_name'] == user:
            user_id = name['user_id']
            break  # No need to continue running once found

    if user_id:
        return user_id
    else:
        print(f"User {user} was not found in the database...")
        return None


def purge(delete, users, org_id=ORG_ID, api_key=API_KEY):
    """Purges all users that aren't marked as safe/persistent"""
    if not delete:
        print("There's nothing here")
        return

    print("\nPurging...")

    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    for user in delete:
        # Format the URL
        url = USER_CONTROL_URL + "?user_id=" + user + "&org_id=" + org_id

        print(f"Running for user: {printName(user, users)}")

        response = requests.delete(url, headers=headers)

        if response.status_code != 200:
            print(f"An error has occured. Status code {response.status_code}")
            return 2  # Completed unsuccesfully

    print("Purge complete.")
    return 1  # Completed


def printName(to_delete, users):
    """Returns the full name with a given ID"""
    user_name = None  # Pre-define

    for user in users:
        if user.get('user_id') == to_delete:
            user_name = user.get('full_name')
            break  # No need to continue running once found

    if user_name:
        return user_name
    else:
        print(f"User {to_delete} was not found in the database...")
        return "Error finding name"


def run():
    """Allows the program to be ran if being imported as a module"""
    print("Retrieving users")
    users = getUsers()
    print("Users retrieved.\n")

    # Run if users were found
    if users:
        print("Gather IDs")
        all_user_ids = getIds(users)
        all_user_ids = cleanList(all_user_ids)
        print("IDs aquired.\n")

        safe_user_ids = []

        # Create the list of safe users
        print("Searching for safe users.")
        for user in PERSISTENT_USERS:
            safe_user_ids.append(getUserId(user, users))
        safe_user_ids = cleanList(safe_user_ids)
        print("Safe users found.\n")

        # New list that filters users that are safe
        users_to_delete = [
            user for user in all_user_ids if user not in safe_user_ids]

        if users_to_delete:
            purge(users_to_delete, users)
            return 1  # Completed

        else:
            print("-------------------------------")
            print(
                "The organization has already been purged.\
                      There are no more users to delete.")
            print("-------------------------------")

            return 1  # Completed
    else:
        print("No users were found.")

        return 1  # Copmleted


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    run()
