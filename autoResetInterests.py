# Author: Ian Young
# Purpose: Compare plates to a pre-defined array of names.
# These names will be "persistent plates/persons" which are to remain in 
# Command. Any person or plate not marked thusly will be deleted from the org.

import creds, logging, requests, threading, time

ORG_ID = creds.lab_id
API_KEY = creds.lab_key

# This will help prevent exceeding the call limit
CALL_COUNT = 0
CALL_COUNT_LOCK = threading.Lock()

# Set logger
log = logging.getLogger()
log.setLevel(logging.WARNING)
logging.basicConfig(
    level = logging.INFO,
    format = "%(levelname)s: %(message)s"
    )
# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Set the full name for which plates are to be persistent
PERSISTENT_PLATES = sorted([''])  # Label of plate !Not plate number!
PERSISTENT_PERSONS = sorted([''])  # PoI label

# Set API endpoint URLs
PLATE_URL = "https://api.verkada.com/cameras/v1/\
analytics/lpr/license_plate_of_interest"
PERSON_URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"

##############################################################################
                                #  Misc  #
##############################################################################


class APIThrottleException(Exception):
    pass


def cleanList(list):
    """Removes any None values from error codes"""
    cleaned_list = [value for value in list if value is not None]
    return cleaned_list


##############################################################################
                         #  All things people  #
##############################################################################


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

        try:
            iter(persons)
        except (TypeError, AttributeError):
            log.error("People are not iterable.")
            return


        try:
            iter(persons)
        except (TypeError, AttributeError):
            log.error(
                f"Cannot convert plates into a tree."
                f"Plates are not iterable."
                )
            
            return

        return persons
    else:
        log.critical(
            f"Person - Error with retrieving persons.\
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
        log.warning(f"Person {person} was not found in the database...")
        return None


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
            log.warning(f"Person - Timed out.")

        elif response.status_code == 400:
            log.warning(f"Person - Contact support: endpoint failure")
        
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
            break  # No need to continue running once found

    if person_name:
        return person_name
    else:
        return "No name provided"


def runPeople():
    """Allows the program to be ran if being imported as a module"""
    # Uncomment the lines below if you want to manually set these values
    # each time the program is ran

    log.info("Retrieving persons")
    persons = getPeople()
    log.info("persons retrieved.")

    # Sort JSON dictionaries by person id
    persons = sorted(persons, key=lambda x: x['person_id'])

    #Run if persons were found
    if persons:
        log.info("Person - Gather IDs")
        all_person_ids = getPeopleIds(persons)
        all_person_ids = cleanList(all_person_ids)
        log.info("Person - IDs aquired.")

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
            # purgePeople(persons_to_delete, persons)
            return 1  # Completed

        else:
            log.info(
                "Person - The organization has already been purged.\
There are no more persons to delete.")

            return 1  # Completed
    else:
        log.warning("No persons were found.")

        return 1  # Copmleted


##############################################################################
                            #  All things plates  #
##############################################################################


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
        
        try:
            # Check if the list is iterable
            iter(plates)
        except (TypeError, AttributeError):
            log.error("Plates are not iterable.")
            return

        return plates
    else:
        log.critical(
            f"Plate - Error with retrieving plates.\
Status code {response.status_code}")
        return


def getPlateIds(plates=None):
    """Returns an array of all LPoI labels in an organization"""
    plate_id = []

    for plate in plates:
        if plate.get('license_plate'):
            plate_id.append(plate.get('license_plate'))
        else:
            log.error(
                f"Plate - There has been an error with plate {plate.get('label')}.")

    return plate_id


def getPlateId(plate=PERSISTENT_PLATES, plates=None):
    """Returns the Verkada ID for a given LPoI"""
    plate_id = None  # Pre-define

    for name in plates:
        if name['description'] == plate:
            plate_id = name['license_plate']
            break  # No need to continue running once found

    if plate_id:
        return plate_id
    else:
        log.error(f"Plate {plate} was not found in the database...")
        return None


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
        
        elif response.status_code == 400:
            log.warning(f"Plate - Contact support: endpoint failure")

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
        return "No name provided"


def runPlates():
    """Allows the program to be ran if being imported as a module"""
    log.info("Retrieving plates")
    plates = getPlates()
    log.info("Plates retrieved.")

    # Sort the JSON dictionaries by plate id
    plates = sorted(plates, key=lambda x: x['plate_id'])

    # Run if plates were found
    if plates:
        log.info("Plate - Gather IDs")
        all_plate_ids = getPlateIds(plates)
        all_plate_ids = cleanList(all_plate_ids)
        log.info("Plate - IDs aquired.")

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
            purgePlates(plates_to_delete, plates)
            return 1  # Completed

        else:
            log.info(
                "The organization has already been purged.\
There are no more plates to delete.")

            return 1  # Completed
    else:
        log.info("No plates were found.")

        return 1  # Copmleted


##############################################################################
                                #  Main  #
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    if GPIO:
        GPIO.output(work_pin, True)
        
    start_time = time.time()
    PoI = threading.Thread(target=runPeople)
    LPoI = threading.Thread(target=runPlates)

    # Start the threads running independantly
    PoI.start()
    LPoI.start()

    # Join the threads back to parent process
    PoI.join()
    LPoI.join()
    elapsed_time = time.time() - start_time

    log.info(f"Total time to complete: {elapsed_time}") 
