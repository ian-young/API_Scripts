import logging, requests, threading, time
from os import getenv
from dotenv import load_dotenv

load_dotenv()

# API credentials
ORG_ID = getenv("lab_id")
API_KEY = getenv("lab_key")

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
PERSISTENT_PLATES = []
PERSISTENT_PERSONS = []

# Set API endpoint URLs
PLATE_URL = "https://api.verkada.com/cameras/v1/\
analytics/lpr/license_plate_of_interest"
PERSON_URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"
USER_INFO_URL = "https://api.verkada.com/access/v1/access_users"
USER_CONTROL_URL = "https://api.verkada.com/core/v1/user"


##############################################################################
                                #  Misc  #
##############################################################################


class APIThrottleException(Exception):
    """
    Exception raised when the API request rate limit is exceeded.

    :param message: A human-readable description of the exception.
    :type message: str
    """
    def __init__(self, message="API throttle limit exceeded."):
        self.message = message
        super.__init__(self.message)


def warn():
    """
    Prints a warning message before continuing
    
    :return: None
    :rtype: None
    """
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
    """
    Removes any None values from error codes
    
    :param list: The list to be cleaned.
    :type list: list
    :return: A new list with None values removed.
    :rtype: list
    """
    cleaned_list = [value for value in list if value is not None]
    return cleaned_list


##############################################################################
                         #  All things people  #
##############################################################################


def checkPeople(safe, to_delete, persons):
    """
    Checks with the user before continuing with the purge.
    
    :param safe: List of PoIs that are marked as "safe."
    :type safe: list
    :param to_delete: List of PoIs that are marked for deletion.
    :type to_delete: list
    :param persons: List of of PoIs retrieved from the organization.
    :type persons: list
    :return: None
    :rtype: None
    """
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
            purgePeople(to_delete, persons)

        else:
            print("Invalid input. Please enter '1', '2', or '3'.")


def getPeople(org_id=ORG_ID, api_key=API_KEY):
    """
    Returns JSON-formatted persons in a Command org.
    
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: A List of dictionaries of people in an organization.
    :rtype: list
    """
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

    for person in persons:
        if person.get('person_id'):
            person_id.append(person.get('person_id'))
        else:
            log.error(
                f"There has been an error with person {person.get('label')}.")

    return person_id


def getPersonId(person, persons=None):
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

        # Make sure the other threads aren't writing
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
    """
    Allows the program to be ran if being imported as a module.
    
    :return: Returns the value 1 if the program completed successfully.
    :rtype: int
    """
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
            person for person in all_person_ids 
            if person not in safe_person_ids]

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
    """
    Checks with the user before continuing with the purge.
    
    :param safe: List of plates that are marked as "safe."
    :type safe: list
    :param to_delete: List of plates that are marked for deletion.
    :type to_delete: list
    :param plates: List of of LPoIs retrieved from the organization.
    :type plates: list
    :return: None
    :rtype: None
    """
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
            purgePlates(to_delete, plates)

        else:
            print("Invalid input. Please enter '1', '2', or '3'.")


def getPlates(org_id=ORG_ID, api_key=API_KEY):
    """
    Returns JSON-formatted plates in a Command org.
    
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: A List of dictionaries of license plates in an organization.
    :rtype: list
    """
    global CALL_COUNT

    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    params = {
        "org_id": org_id,
    }

    response = requests.get(PLATE_URL, headers=headers, params=params)

    # Make sure the other threads aren't writing
    with CALL_COUNT_LOCK:
        CALL_COUNT += 1  # Log that a thread was made

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

    for plate in plates:
        if plate.get('license_plate'):
            plate_id.append(plate.get('license_plate'))
        else:
            log.error(
                f"There has been an error with plate {plate.get('label')}.")

    return plate_id


def getPlateId(plate=PERSISTENT_PLATES, plates=None):
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
    plate_id = None  # Pre-define

    for name in plates:
        if name['description'] == plate:
            plate_id = name['license_plate']
            break  # No need to continue running once found

    if plate_id:
        return plate_id
    else:
        return "No name provided"


def delete_plate(plate, plates, org_id=ORG_ID, api_key=API_KEY):
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
    """
    Allows the program to be ran if being imported as a module.
    
    :return: Returns the value 1 if the program completed successfully.
    :rtype: int
    """
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

        return 1  # Completed


##############################################################################
                                #  Main  #
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    warn()

    # Pre-define responses
    run_poi = False
    run_lpoi = False
    answer = None

    # Define threads
    poi_thread = threading.Thread(target=runPeople)
    lpoi_thread = threading.Thread(target=runPlates)
    
    while answer not in ['y', 'n']:
        answer = str(input("Would you like to run for PoI?(y/n) "))\
            .strip().lower()
        
        if answer == 'y':
            run_poi = True
    
    answer = None  # Reset response
    while answer not in ['y', 'n']:
            answer = str(input("Would you like to run for LPoI?(y/n) "))\
                .strip().lower()
                
            if answer == 'y':
                run_lpoi = True

    # Time the runtime
    start_time = time.time()

    # Start threads
    if run_poi:
        poi_thread.start()
    if run_lpoi:
        lpoi_thread.start()

    # Join back to main thread
    if run_poi:
        poi_thread.join()
    if run_lpoi:
        lpoi_thread.join()

    # Wrap up in a bow and complete
    log.info(f"Time to complete: {time.time() - start_time}")
    print("Exiting...")
                
