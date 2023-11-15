# Author: Ian Young
# Purpose: Compare plates to a pre-defined array of names.
# These names will be "persistent" which are to remain in Command.
# Anything not marked thusly will be deleted from the org.

import creds, logging, requests, threading, time

ORG_ID = creds.lab_id
API_KEY = creds.lab_key

# Set logger
log = logging.getLogger()
logging.basicConfig(
    level = logging.INFO,
    format = "%(levelname)s: %(message)s"
)

# This will help prevent exceeding the call limit
CALL_COUNT = 0
CALL_COUNT_LOCK = threading.Lock()

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


class APIThrottleException(Exception):
    pass


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
        cont = str(input("Press enter to continue")).strip()


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
    global CALL_COUNT

    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    params = {
        "org_id": org_id,
    }

    response = requests.get(PERSON_URL, headers=headers, params=params)
    
    with CALL_COUNT_LOCK:
        CALL_COUNT += 1

    if response.status_code == 200:
        data = response.json()  # Parse the response

        # Extract as a list
        persons = data.get('persons_of_interest')
        return persons
    else:
        log.critical(
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
            log.error(
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
        return "No name provided"


def delete_person(person, persons, org_id=ORG_ID, api_key=API_KEY):
    """Deletes the given person"""
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    log.info(f"Running for person: {printPersonName(person, persons)}")

    params = {
        'org_id': org_id,
        'person_id': person
    }

    try:
        # Stop running if already at the limit
        if CALL_COUNT >= 500:
            return
        response = requests.delete(PERSON_URL, headers=headers, params=params)
    
        if response.status_code == 429:
            raise APIThrottleException("API throttled")
        
        elif response.status_code == 504:
            log.warning(f"Plate - Timed out.")
        
        elif response.status_code != 200:
            log.error(f"\
Person - An error has occured. Status code {response.status_code}")
        
    except APIThrottleException:
                    log.critical("Person - Hit API request rate limit of 500 requests per minute.")



def purgePeople(delete, persons, org_id=ORG_ID, api_key=API_KEY):
    """Purges all PoIs that aren't marked as safe/persistent"""
    global CALL_COUNT

    if not delete:
        log.warning("Person - There's nothing here")
        return

    log.info("Person - Purging...")

    start_time = time.time()
    threads = []
    for person in delete:
        # Stop making threads if already at the limit
        if CALL_COUNT >= 500:
            return
        
        # Toss delete function into a new thread
        thread = threading.Thread(
            target=delete_person, args=(person, persons, org_id, api_key)
        )
        thread.start()
        threads.append(thread)  # Add the thread to the pile

        # Make sure the other thread isn't writing
        with CALL_COUNT_LOCK:
            CALL_COUNT += 1  # Log that the thread was made

    for thread in threads:
        thread.join()  # Join back to main thread

    end_time = time.time()
    elapsed_time = str(end_time - start_time)

    log.info("Person - Purge complete.")
    log.info(f"Person - Time to complete: {elapsed_time}")
    return 1  # Completed


def printPersonName(to_delete, persons):
    """Returns the full name with a given ID"""
    person_name = None  # Pre-define

    for person in persons:
        if person.get('person_id') == to_delete:
            person_name = person.get('label')
            return  # No need to continue running once found

    if person_name:
        return person_name
    else:
        return "No name provided"


def runPeople():
    """Allows the program to be ran if being imported as a module"""
    # Uncomment the lines below if you want to manually set these values
    # each time the program is ran

    # org = str(input("Org ID: ""))
    # key = str(input("API key: "))

    log.info("Retrieving persons")
    persons = getPeople()
    log.info("persons retrieved.")

    # Run if persons were found
    if persons:
        log.info("Gather IDs")
        all_person_ids = getPeopleIds(persons)
        all_person_ids = cleanList(all_person_ids)
        log.info("IDs aquired.")

        safe_person_ids = []

        log.info("Searching for safe persons.")
        # Create the list of safe persons
        for person in PERSISTENT_PERSONS:
            safe_person_ids.append(getPersonId(person, persons))
        safe_person_ids = cleanList(safe_person_ids)
        log.info("Safe persons found.")

        # New list that filters persons that are safe
        persons_to_delete = [
            person for person in all_person_ids if person not in safe_person_ids]

        if persons_to_delete:
            checkPeople(safe_person_ids, persons_to_delete, persons)
            return 1  # Completed

        else:
            log.warning(
                "The organization has already been purged.\
There are no more persons to delete.")
            return 1  # Completed
        
    else:
        log.warning("No persons were found.")
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
    global CALL_COUNT

    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    params = {
        "org_id": org_id,
    }

    response = requests.get(PLATE_URL, headers=headers, params=params)

    with CALL_COUNT_LOCK:
        CALL_COUNT += 1

    if response.status_code == 200:
        data = response.json()  # Parse the response

        # Extract as a list
        plates = data.get('license_plate_of_interest')
        return plates
    else:
        log.critical(
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
            log.error(
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
        return "No name provided"


def delete_plate(plate, plates, org_id=ORG_ID, api_key=API_KEY):
    """Deletes the given person"""
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    log.info(f"Running for plate: {printPlateName(plate, plates)}")

    params = {
        'org_id': org_id,
        'license_plate': plate
    }

    try:
        # Stop running if already at the limit
        if CALL_COUNT >= 500:
            return
        response = requests.delete(PLATE_URL, headers=headers, params=params)
    
        if response.status_code == 429:
            raise APIThrottleException("API throttled")
        
        elif response.status_code == 504:
            log.warning(f"Plate - Timed out.")

        elif response.status_code != 200:
            log.error(f"\
Plate - An error has occured. Status code {response.status_code}")
        
    except APIThrottleException:
                    log.critical("Plate - Hit API request rate limit of 500 requests per minute.")


def purgePlates(delete, plates, org_id=ORG_ID, api_key=API_KEY):
    """Purges all LPoIs that aren't marked as safe/persistent"""
    global CALL_COUNT
    
    if not delete:
        log.warning("Plate - There's nothing here")
        return

    log.info("Plate - Purging...")

    start_time = time.time()
    threads = []
    for plate in delete:
        # Stop making threads if already at the limit
        if CALL_COUNT >= 500:
            return
        
        # Toss delete function into a new thread
        thread = threading.Thread(
            target=delete_plate, args=(plate, plates, org_id, api_key)
        )
        thread.start()
        threads.append(thread)  # Add the thread to the pile

        # Make sure the other thread isn't writing
        with CALL_COUNT_LOCK:
            CALL_COUNT += 1  # Log that the thread was made

    for thread in threads:
        thread.join()  # Join back to main thread

    end_time = time.time()
    elapsed_time = str(end_time - start_time)

    log.info("Plate - Purge complete.")
    log.info(f"Plate - Time to complete: {elapsed_time}")
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
        return "No name provided."


def runPlates():
    """Allows the program to be ran if being imported as a module"""
    # Uncomment the lines below if you want to manually set these values
    # each time the program is ran

    # org = str(input("Org ID: ""))
    # key = str(input("API key: "))

    log.info("Retrieving plates")
    plates = getPlates()
    log.info("plates retrieved.")

    # Run if plates were found
    if plates:
        log.info("Gather IDs")
        all_plate_ids = getPlateIds(plates)
        all_plate_ids = cleanList(all_plate_ids)
        log.info("IDs aquired.")

        safe_plate_ids = []

        log.info("Searching for safe plates.")
        # Create the list of safe plates
        for plate in PERSISTENT_PLATES:
            safe_plate_ids.append(getPlateId(plate, plates))
        safe_plate_ids = cleanList(safe_plate_ids)
        log.info("Safe plates found.")

        # New list that filters plates that are safe
        plates_to_delete = [
            plate for plate in all_plate_ids if plate not in safe_plate_ids]

        if plates_to_delete:
            checkPlates(safe_plate_ids, plates_to_delete, plates)
            return 1  # Completed

        else:
            log.warning(
                "The organization has already been purged.\
There are no more plates to delete.")

            return 1  # Completed
    else:
        log.warning("No plates were found.")

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
    global CALL_COUNT

    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    params = {
        "org_id": org_id,
    }

    response = requests.get(USER_INFO_URL, headers=headers, params=params)

    with CALL_COUNT_LOCK:
        CALL_COUNT += 1

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


def delete_user(user, users, org_id=ORG_ID, api_key=API_KEY):
    """Deletes the given user"""
    # Format the URL
    url = USER_CONTROL_URL + "?user_id=" + user + "&org_id=" + org_id

    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    log.info(f"Running for user: {printUserName(user, users)}")
    
    # Stop if at call limit
    if CALL_COUNT >= 500:
        return
    
    response = requests.delete(url, headers=headers)

    if response.status_code != 200:
        log.error(
            f"An error has occured. Status code {response.status_code}")
        return 2  # Completed unsuccesfully


def purgeUsers(delete, users, org_id=ORG_ID, api_key=API_KEY):
    """Purges all users that aren't marked as safe/persistent"""
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
        log.warning(f"User {to_delete} was not found in the database...")
        return "Error finding name"
    

def runUsers():
    """Allows the program to be ran if being imported as a module"""
    # org = str(input("Org ID: ""))
    # key = str(input("API key: "))

    warn()

    log.info("Retrieving users")
    users = getUsers()
    log.info("Users retrieved.")

    # Run if users were found
    if users:
        log.info("Gather IDs")
        all_user_ids = getUserIds(users)
        all_user_ids = cleanList(all_user_ids)
        log.info("IDs aquired.")

        safe_user_ids = []

        log.info("Searching for safe users.")
        # Create the list of safe users
        for user in PERSISTENT_USERS:
            safe_user_ids.append(getUserId(user, users))
        safe_user_ids = cleanList(safe_user_ids)
        log.info("Safe users found.")

        # New list that filters users that are safe
        users_to_delete = [
            user for user in all_user_ids if user not in safe_user_ids]

        if users_to_delete:
            checkUsers(safe_user_ids, users_to_delete, users)
            return 1  # Completed

        else:
            log.warning(
                "The organization has already been purged.\
                      There are no more users to delete.")

            return 1  # Completed
        

##############################################################################
                                #  Main  #
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    warn()
    run_poi = False
    run_lpoi = False
    run_user = False
    
    poi_thread = threading.Thread(target=runPeople)
    lpoi_thread = threading.Thread(target=runPlates)
    user_thread = threading.Thread(target=runUsers)

    answer = None
    while answer not in ['y', 'n']:
        answer = str(input("Would you like to run for users?(y/n) "))\
        .strip().lower()

        if answer == 'y':
            run_user = True
    
    answer = None
    while answer not in ['y', 'n']:
        answer = str(input("Would you like to run for PoI?(y/n) "))\
            .strip().lower()
        
        if answer == 'y':
            run_poi = True
    
    answer = None
    while answer not in ['y', 'n']:
            answer = str(input("Would you like to run for LPoI?(y/n) "))\
                .strip().lower()
                
            if answer == 'y':
                run_lpoi = True

    # Time the runtime
    start_time = time.time()

    # Start threads
    if run_user:
        user_thread.start()
    if run_poi:
        poi_thread.start()
    if run_lpoi:
        lpoi_thread.start()

    # Join back to main thread
    if run_user:
        user_thread.join()
    if run_poi:
        poi_thread.join()
    if run_lpoi:
        lpoi_thread.join()

    # Wrap up in a bow and complete
    log.info(f"Time to complete: {time.time() - start_time}")
    print("Exiting...")
