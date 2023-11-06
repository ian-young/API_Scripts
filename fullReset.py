# Author: Ian Young
# Purpose: Compare plates to a pre-defined array of names.
# These names will be "persistent" which are to remain in Command.
# Anything not marked thusly will be deleted from the org.

import requests

ORG_ID = "16f37a49-2c89-4bd9-b667-a28af7700068"
API_KEY = "vkd_api_356c542f37264c99a6e1f95cac15f6af"

# Set the full name for which plates are to be persistent
PERSISTENT_PLATES = ["Random"]
PERSISTENT_PERSONS = ["PoI"]
PERSISTENT_USERS = ["Ian Young", "Bruce Banner",
                    "Jane Doe", "Tony Stark",
                    "Ray Raymond", "John Doe"] # Must use full name

# Set API endpoint URLs
PLATE_URL = "https://api.verkada.com/cameras/v1/analytics/lpr/license_plate_of_interest"
PERSON_URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"
USER_INFO_URL = "https://api.verkada.com/access/v1/access_users"
USER_CONTROL_URL = "https://api.verkada.com/core/v1/user"


##############################################################################
                                #  Misc  #
##############################################################################


def warn():
    """Prints a warning message before continuing"""
    print("-------------------------------")
    print("WARNING!!!")
    print("Please make sure you have changed the persistent plates variable.")
    print("Otherwise all of your plates will be deleted.")
    print("Please double-check spelling, as well!")
    print("-------------------------------")
    cont = None

    while cont not in ["", " "]:
        cont = str(input("Press enter to continue\n")).strip()


def cleanList(list):
    """Removes any None values from error codes"""
    cleaned_list = [value for value in list if value is not None]
    return cleaned_list


##############################################################################
                         #  All things people  #
##############################################################################


def checkPeople(safe, to_delete, persons):
    """Checks with the user before continuing with the purge"""
    trust_level = None  # Pre-define
    ok = None  # Pre-define

    while trust_level not in ['1', '2', '3']:
        print("1. Check marked persistent persons against what the \
application found.")
        print("2. Check what is marked for deletion by the application.")
        print("3. Trust the process and blindly move forward.")

        trust_level = str(input('- ')).strip()

        if trust_level == '1':
            print("-------------------------------")
            print("Please check that the two lists match: ")

            safe_names = [printPersonName(person_id, persons)
                          for person_id in safe]

            print(", ".join(safe_names))
            print("vs")
            print(", ".join(PERSISTENT_PERSONS))
            print("-------------------------------")

            while ok not in ['y', 'n']:
                ok = str(input("Do they match?(y/n) ")).strip().lower()

                if ok == 'y':
                    purgePeople(to_delete, persons)

                elif ok == 'n':
                    print("Please check the input values")
                    print("Exiting...")

                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

        elif trust_level == '2':
            print("-------------------------------")
            print("Here are the persons being purged: ")

            delete_names = \
                [printPersonName(person_id, persons)
                 for person_id in to_delete]
            print(", ".join(delete_names))
            print("-------------------------------")

            while ok not in ['y', 'n']:
                ok = \
                    str(input("Is this list accurate?(y/n) ")).strip().lower()

                if ok == 'y':
                    purgePeople(to_delete, persons)

                elif ok == 'n':
                    print("Please check the input values.")
                    print("Exiting...")

                else:
                    print("Invalud input. Please enter 'y' or 'n'.")

        elif trust_level == '3':
            print("Good luck!")
            purgePeople(to_delete)

        else:
            print("Invalid input. Please enter '1', '2', or '3'.")


def getPeople(org_id=ORG_ID, api_key=API_KEY):
    """Returns JSON-formatted persons in a Command org"""
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    params = {
        "org_id": org_id,
    }

    response = requests.get(PERSON_URL, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()  # Parse the response

        # Extract as a list
        persons = data.get('persons_of_interest')
        return persons
    else:
        print(
            f"Error with retrieving persons.\
Status code {response.status_code}")
        return None


def getPeopleIds(persons=None):
    """Returns an array of all PoI labels in an organization"""
    person_id = []

    for person in persons:
        if person.get('person_id'):
            person_id.append(person.get('person_id'))
        else:
            print(
                f"There has been an error with person {person.get('label')}.")

    return person_id


def getPersonId(person=PERSISTENT_PERSONS, persons=None):
    """Returns the Verkada ID for a given PoI"""
    person_id = None  # Pre-define

    for name in persons:
        if name['label'] == person:
            person_id = name['person_id']
            break  # No need to continue running once found

    if person_id:
        return person_id
    else:
        print(f"person {person} was not found in the database...")
        return None


def purgePeople(delete, persons, org_id=ORG_ID, api_key=API_KEY):
    """Purges all PoIs that aren't marked as safe/persistent"""
    if not delete:
        print("There's nothing here")
        return

    print("\nPurging...")

    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    for person in delete:
        print(f"Running for person: {printPersonName(person, persons)}")

        params = {
            'org_id': org_id,
            'person_id': person
        }

        response = requests.delete(PERSON_URL, headers=headers, params=params)

        if response.status_code != 200:
            print(f"An error has occured. Status code {response.status_code}")
            return 2  # Completed unsuccesfully

    print("Purge complete.")
    return 1  # Completed


def printPersonName(to_delete, persons):
    """Returns the full name with a given ID"""
    person_name = None  # Pre-define

    for person in persons:
        if person.get('person_id') == to_delete:
            person_name = person.get('label')
            break  # No need to continue running once found

    if person_name:
        return person_name
    else:
        print(f"person {to_delete} was not found in the database...")
        return "Error finding name"


def runPeople():
    """Allows the program to be ran if being imported as a module"""
    # Uncomment the lines below if you want to manually set these values
    # each time the program is ran

    # org = str(input("Org ID: ""))
    # key = str(input("API key: "))

    print("Retrieving persons")
    persons = getPeople()
    print("persons retrieved.\n")

    # Run if persons were found
    if persons:
        print("Gather IDs")
        all_person_ids = getPeopleIds(persons)
        all_person_ids = cleanList(all_person_ids)
        print("IDs aquired.\n")

        safe_person_ids = []

        print("Searching for safe persons.")
        # Create the list of safe persons
        for person in PERSISTENT_PERSONS:
            safe_person_ids.append(getPersonId(person, persons))
        safe_person_ids = cleanList(safe_person_ids)
        print("Safe persons found.\n")

        # New list that filters persons that are safe
        persons_to_delete = [
            person for person in all_person_ids if person not in safe_person_ids]

        if persons_to_delete:
            checkPeople(safe_person_ids, persons_to_delete, persons)
            return 1  # Completed

        else:
            print("-------------------------------")
            print(
                "The organization has already been purged.\
There are no more persons to delete.")
            print("-------------------------------")

            return 1  # Completed
    else:
        print("No persons were found.")

        return 1  # Copmleted


##############################################################################
                            #  All things plates  #
##############################################################################


def checkPlates(safe, to_delete, plates):
    """Checks with the user before continuing with the purge"""
    trust_level = None  # Pre-define
    ok = None  # Pre-define

    while trust_level not in ['1', '2', '3']:
        print("1. Check marked persistent plates against what the \
application found.")
        print("2. Check what is marked for deletion by the application.")
        print("3. Trust the process and blindly move forward.")

        trust_level = str(input('- ')).strip()

        if trust_level == '1':
            print("-------------------------------")
            print("Please check that the two lists match: ")

            safe_names = [printPlateName(plate_id, plates)
                          for plate_id in safe]

            print(", ".join(safe_names))
            print("vs")
            print(", ".join(PERSISTENT_PLATES))
            print("-------------------------------")

            while ok not in ['y', 'n']:
                ok = str(input("Do they match?(y/n) ")).strip().lower()

                if ok == 'y':
                    purgePlates(to_delete, plates)

                elif ok == 'n':
                    print("Please check the input values")
                    print("Exiting...")

                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

        elif trust_level == '2':
            print("-------------------------------")
            print("Here are the plates being purged: ")

            delete_names = \
                [printPlateName(plate_id, plates) for plate_id in to_delete]
            print(", ".join(delete_names))
            print("-------------------------------")

            while ok not in ['y', 'n']:
                ok = \
                    str(input("Is this list accurate?(y/n) ")).strip().lower()

                if ok == 'y':
                    purgePlates(to_delete, plates)

                elif ok == 'n':
                    print("Please check the input values.")
                    print("Exiting...")

                else:
                    print("Invalud input. Please enter 'y' or 'n'.")

        elif trust_level == '3':
            print("Good luck!")
            purgePlates(to_delete)

        else:
            print("Invalid input. Please enter '1', '2', or '3'.")


def getPlates(org_id=ORG_ID, api_key=API_KEY):
    """Returns JSON-formatted plates in a Command org"""
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    params = {
        "org_id": org_id,
    }

    response = requests.get(PLATE_URL, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()  # Parse the response

        # Extract as a list
        plates = data.get('license_plate_of_interest')
        return plates
    else:
        print(
            f"Error with retrieving plates.\
Status code {response.status_code}")
        return None


def getPlateIds(plates=None):
    """Returns an array of all PoI labels in an organization"""
    plate_id = []

    for plate in plates:
        if plate.get('license_plate'):
            plate_id.append(plate.get('license_plate'))
        else:
            print(
                f"There has been an error with plate {plate.get('label')}.")

    return plate_id


def getPlateId(plate=PERSISTENT_PLATES, plates=None):
    """Returns the Verkada ID for a given PoI"""
    plate_id = None  # Pre-define

    for name in plates:
        if name['description'] == plate:
            plate_id = name['plate_id']
            break  # No need to continue running once found

    if plate_id:
        return plate_id
    else:
        print(f"plate {plate} was not found in the database...")
        return None


def purgePlates(delete, plates, org_id=ORG_ID, api_key=API_KEY):
    """Purges all PoIs that aren't marked as safe/persistent"""
    if not delete:
        print("There's nothing here")
        return

    print("\nPurging...")

    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    for plate in delete:
        print(f"Running for plate: {printPlateName(plate, plates)}")

        params = {
            'org_id': org_id,
            'plate_id': plate
        }

        response = requests.delete(PLATE_URL, headers=headers, params=params)

        if response.status_code != 200:
            print(f"An error has occured. Status code {response.status_code}")
            return 2  # Completed unsuccesfully

    print("Purge complete.")
    return 1  # Completed


def printPlateName(to_delete, plates):
    """Returns the full name with a given ID"""
    plate_name = None  # Pre-define

    for plate in plates:
        if plate.get('license_plate') == to_delete:
            plate_name = plate.get('description')
            break  # No need to continue running once found

    if plate_name:
        return plate_name
    else:
        print(f"plate {to_delete} was not found in the database...")
        return "Error finding name"


def runPlates():
    """Allows the program to be ran if being imported as a module"""
    # Uncomment the lines below if you want to manually set these values
    # each time the program is ran

    # org = str(input("Org ID: ""))
    # key = str(input("API key: "))

    print("Retrieving plates")
    plates = getPlates()
    print("plates retrieved.\n")

    # Run if plates were found
    if plates:
        print("Gather IDs")
        all_plate_ids = getPlateIds(plates)
        all_plate_ids = cleanList(all_plate_ids)
        print("IDs aquired.\n")

        safe_plate_ids = []

        print("Searching for safe plates.")
        # Create the list of safe plates
        for plate in PERSISTENT_PLATES:
            safe_plate_ids.append(getPlateId(plate, plates))
        safe_plate_ids = cleanList(safe_plate_ids)
        print("Safe plates found.\n")

        # New list that filters plates that are safe
        plates_to_delete = [
            plate for plate in all_plate_ids if plate not in safe_plate_ids]

        if plates_to_delete:
            checkPlates(safe_plate_ids, plates_to_delete, plates)
            return 1  # Completed

        else:
            print("-------------------------------")
            print(
                "The organization has already been purged.\
There are no more plates to delete.")
            print("-------------------------------")

            return 1  # Completed
    else:
        print("No plates were found.")

        return 1  # Copmleted


##############################################################################
                            #  All things plates  #
##############################################################################


def checkUsers(safe, to_delete, users):
    """Checks with the user before continuing with the purge"""
    trust_level = None  # Pre-define
    ok = None  # Pre-define

    while trust_level not in ['1', '2', '3']:
        print("1. Check marked persistent users against what the \
application found.")
        print("2. Check what is marked for deletion by the application.")
        print("3. Trust the process and blindly move forward.")

        trust_level = str(input('- ')).strip()

        if trust_level == '1':
            print("-------------------------------")
            print("Please check that the two lists match: ")

            safe_names = [printUserName(user_id, users) for user_id in safe]

            print(", ".join(safe_names))
            print("vs")
            print(", ".join(PERSISTENT_USERS))
            print("-------------------------------")

            while ok not in ['y', 'n']:
                ok = str(input("Do they match?(y/n) ")).strip().lower()

                if ok == 'y':
                    purgeUsers(to_delete, users)

                elif ok == 'n':
                    print("Please check the input values")
                    print("Exiting...")

                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

        elif trust_level == '2':
            print("-------------------------------")
            print("Here are the users being purged: ")

            delete_names = \
                [printUserName(user_id, users) for user_id in to_delete]
            print(", ".join(delete_names))
            print("-------------------------------")

            while ok not in ['y', 'n']:
                ok = \
                    str(input("Is this list accurate?(y/n) ")).strip().lower()

                if ok == 'y':
                    purgeUsers(to_delete, users)

                elif ok == 'n':
                    print("Please check the input values.")
                    print("Exiting...")

                else:
                    print("Invalud input. Please enter 'y' or 'n'.")

        elif trust_level == '3':
            print("Good luck!")
            purgeUsers(to_delete)

        else:
            print("Invalid input. Please enter '1', '2', or '3'.")

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


def getUserIds(users=None):
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


def purgeUsers(delete, users, org_id=ORG_ID, api_key=API_KEY):
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

        print(f"Running for user: {printUserName(user, users)}")

        response = requests.delete(url, headers=headers)

        if response.status_code != 200:
            print(f"An error has occured. Status code {response.status_code}")
            return 2  # Completed unsuccesfully

    print("Purge complete.")
    return 1  # Completed


def printUserName(to_delete, users):
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
    

def runUsers():
    """Allows the program to be ran if being imported as a module"""
    # org = str(input("Org ID: ""))
    # key = str(input("API key: "))

    warn()

    print("Retrieving users")
    users = getUsers()
    print("Users retrieved.\n")

    # Run if users were found
    if users:
        print("Gather IDs")
        all_user_ids = getUserIds(users)
        all_user_ids = cleanList(all_user_ids)
        print("IDs aquired.\n")

        safe_user_ids = []

        print("Searching for safe users.")
        # Create the list of safe users
        for user in PERSISTENT_USERS:
            safe_user_ids.append(getUserId(user, users))
        safe_user_ids = cleanList(safe_user_ids)
        print("Safe users found.\n")

        # New list that filters users that are safe
        users_to_delete = [
            user for user in all_user_ids if user not in safe_user_ids]

        if users_to_delete:
            checkUsers(safe_user_ids, users_to_delete, users)
            return 1  # Completed

        else:
            print("-------------------------------")
            print(
                "The organization has already been purged.\
                      There are no more users to delete.")
            print("-------------------------------")

            return 1  # Completed
        

##############################################################################
                                #  Main  #
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    warn()

    answer = None
    while answer not in ['y', 'n']:
        answer = str(input("Would you like to run for users?\n(y/n) "))\
        .strip().lower()

        if answer == 'y':
            runUsers()
    
    answer = None
    while answer not in ['y', 'n']:
        answer = str(input("Would you like to run for PoI?\n(y/n) "))\
            .strip().lower()
        
        if answer == 'y':
            runPeople()
    
    answer = None
    while answer not in ['y', 'n']:
            answer = str(input("Would you like to run for LPoI?\n(y/n) "))\
                .strip().lower()
                
            if answer == 'y':
                runPlates()

    print("Exiting...")
