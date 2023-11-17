# Author: Ian Young
# Purpose: Compare plates to a pre-defined array of names.
# These names will be "persistent plates/persons" which are to remain in 
# Command. Any person or plate not marked thusly will be deleted from the org.

import logging, requests, threading, time

ORG_ID = ""
API_KEY = ""

# Set the full name for which plates are to be persistent
PERSISTENT_PLATES = []
PERSISTENT_PERSONS = []

# Set API endpoint URLs
PLATE_URL = "https://api.verkada.com/cameras/v1/\
analytics/lpr/license_plate_of_interest"
PERSON_URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"

##############################################################################
                                #  Misc  #
##############################################################################


def cleanList(list):
    """Removes any None values from error codes"""
    cleaned_list = [value for value in list if value is not None]
    return cleaned_list


##############################################################################
                         #  All things people  #
##############################################################################


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
        logging.error(
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
            logging.error(
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
        logging.warning(f"person {person} was not found in the database...")
        return None


def delete_person(person, persons, org_id=ORG_ID, api_key=API_KEY):
    """Deletes the given person"""
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    logging.info(f"Running for person: {printPersonName(person, persons)}")

    params = {
        'org_id': org_id,
        'person_id': person
    }

    response = requests.delete(PERSON_URL, headers=headers, params=params)

    if response.status_code != 200:
        logging.error(f"\
An error has occured. Status code {response.status_code}")
        return 2  # Completed unsuccesfully


def purgePeople(delete, persons, org_id=ORG_ID, api_key=API_KEY):
    """Purges all PoIs that aren't marked as safe/persistent"""
    if not delete:
        logging.critical("There's nothing here")
        return

    logging.info("\nPurging...")

    start_time = time.time()
    threads = []
    for person in delete:
        thread = threading.Thread(
            target=delete_person, args=(person, persons, org_id, api_key)
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()  # Join back to main thread

    end_time = time.time()
    elapsed_time = str(end_time - start_time)

    logging.info("Purge complete.")
    logging.debug(f"Time to complete: {elapsed_time}")
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
        logging.error(f"person {to_delete} was not found in the database...")
        return "Error finding name"


def runPeople():
    """Allows the program to be ran if being imported as a module"""
    # Uncomment the lines below if you want to manually set these values
    # each time the program is ran

    # org = str(input("Org ID: ""))
    # key = str(input("API key: "))

    logging.info("Retrieving persons")
    persons = getPeople()
    logging.info("persons retrieved.\n")

    # Run if persons were found
    if persons:
        logging.info("Gather IDs")
        all_person_ids = getPeopleIds(persons)
        all_person_ids = cleanList(all_person_ids)
        logging.info("IDs aquired.\n")

        safe_person_ids = []

        logging.info("Searching for safe persons.")
        # Create the list of safe persons
        for person in PERSISTENT_PERSONS:
            safe_person_ids.append(getPersonId(person, persons))
        safe_person_ids = cleanList(safe_person_ids)
        logging.info("Safe persons found.\n")

        # New list that filters persons that are safe
        persons_to_delete = [
            person for person in all_person_ids 
            if person not in safe_person_ids]

        if persons_to_delete:
            purgePeople(persons_to_delete, persons)
            return 1  # Completed

        else:
            logging.info("-------------------------------")
            logging.info(
                "The organization has already been purged.\
There are no more persons to delete.")
            logging.info("-------------------------------")

            return 1  # Completed
    else:
        logging.warning("No persons were found.")

        return 1  # Copmleted


##############################################################################
                            #  All things plates  #
##############################################################################


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
        logging.error(
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
            logging.error(
                f"There has been an error with plate {plate.get('label')}.")

    return plate_id


def getPlateId(plate=PERSISTENT_PLATES, plates=None):
    """Returns the Verkada ID for a given PoI"""
    plate_id = None  # Pre-define

    for name in plates:
        if name['description'] == plate:
            plate_id = name['license_plate']
            break  # No need to continue running once found

    if plate_id:
        return plate_id
    else:
        logging.error(f"plate {plate} was not found in the database...")
        return None


def delete_plate(plate, plates, org_id=ORG_ID, api_key=API_KEY):
    """Deletes the given person"""
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    logging.info(f"Running for plate: {printPlateName(plate, plates)}")

    params = {
        'org_id': org_id,
        'license_plate': plate
    }

    response = requests.delete(PLATE_URL, headers=headers, params=params)

    if response.status_code != 200:
        logging.error(f"\
An error has occured. Status code {response.status_code}")
        return 2  # Completed unsuccesfully


def purgePlates(delete, plates, org_id=ORG_ID, api_key=API_KEY):
    """Purges all PoIs that aren't marked as safe/persistent"""
    if not delete:
        logging.critical("There's nothing here")
        return

    logging.info("\nPurging...")

    start_time = time.time()
    threads = []
    for person in delete:
        thread = threading.Thread(
            target=delete_plate, args=(person, plates, org_id, api_key)
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()  # Join back to main thread

    end_time = time.time()
    elapsed_time = str(end_time - start_time)

    logging.info("Purge complete.")
    logging.debug(f"Time to complete: {elapsed_time}")
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
        logging.error(f"plate {to_delete} was not found in the database...")
        return "Error finding name"


def runPlates():
    """Allows the program to be ran if being imported as a module"""
    logging.info("Retrieving plates")
    plates = getPlates()
    logging.info("plates retrieved.\n")

    # Run if plates were found
    if plates:
        logging.info("Gather IDs")
        all_plate_ids = getPlateIds(plates)
        all_plate_ids = cleanList(all_plate_ids)
        logging.info("IDs aquired.\n")

        safe_plate_ids = []

        logging.info("Searching for safe plates.")
        # Create the list of safe plates
        for plate in PERSISTENT_PLATES:
            safe_plate_ids.append(getPlateId(plate, plates))
        safe_plate_ids = cleanList(safe_plate_ids)
        logging.info("Safe plates found.\n")

        # New list that filters plates that are safe
        plates_to_delete = [
            plate for plate in all_plate_ids if plate not in safe_plate_ids]

        if plates_to_delete:
            purgePlates(plates_to_delete, plates)
            return 1  # Completed

        else:
            logging.info("-------------------------------")
            logging.info(
                "The organization has already been purged.\
There are no more plates to delete.")
            logging.info("-------------------------------")

            return 1  # Completed
    else:
        logging.info("No plates were found.")

        return 1  # Copmleted


##############################################################################
                                #  Main  #
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    PoI = threading.Thread(target=runPeople())
    LPoI = threading.Thread(target=runPlates())

    # Start the threads running independantly
    PoI.start()
    LPoI.start()

    # Join the threads back to parent process
    PoI.join()
    LPoI.join()
