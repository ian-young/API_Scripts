# Author: Ian Young
# Purpose: Compare plates to a pre-defined array of names.
# These names will be "persistent plates" which are to remain in Command.
# Any plate not marked thusly will be deleted from the org.

import creds, logging, requests, threading, time

ORG_ID = creds.lab_id
API_KEY = creds.lab_key

# This will help prevent exceeding the call limit
CALL_COUNT = 0
CALL_COUNT_LOCK = threading.Lock()

# Set logger
log = logging.getLogger()
logging.basicConfig(
    level = logging.INFO,
    format = "%(levelname)s: %(message)s"
    )

# Set the full name for which plates are to be persistent
PERSISTENT_PLATES = ["Random"]

URL = "https://api.verkada.com/cameras/v1/\
analytics/lpr/license_plate_of_interest"


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
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    params = {
        "org_id": org_id,
    }

    response = requests.get(URL, headers=headers, params=params)

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


def getIds(plates=None):
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
        log.warning(f"plate {plate} was not found in the database...")
        return None


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

    log.info(f"Running for plate: {printName(plate, plates)}")

    params = {
        'org_id': org_id,
        'license_plate': plate
    }

    response = requests.delete(URL, headers=headers, params=params)

    if response.status_code != 200:
        log.error(
            f"An error has occured. Status code {response.status_code}")
        return 2  # Completed unsuccesfully


def purge(delete, plates, org_id=ORG_ID, api_key=API_KEY):
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
        log.warning("There's nothing here")
        return

    log.info("Purging...")

    start_time = time.time()
    threads = []
    for person in delete:
        if CALL_COUNT >= 500:
            return

        thread = threading.Thread(
            target=delete_plate, args=(person, plates, org_id, api_key)
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


def printName(to_delete, plates):
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
        log.warning(f"\
plate {to_delete} was not found in the database...")
        return "Error finding name"


def run():
    """
    Allows the program to be ran if being imported as a module.
    
    :return: Returns the value 1 if the program completed successfully.
    :rtype: int
    """
    log.info("Retrieving plates")
    plates = getPlates()
    log.info("plates retrieved.\n")

    # Run if plates were found
    if plates:
        log.info("Gather IDs")
        all_plate_ids = getIds(plates)
        all_plate_ids = cleanList(all_plate_ids)
        log.info("IDs aquired.\n")

        safe_plate_ids = []

        # Create the list of safe plates
        log.info("Searching for safe plates.")
        for plate in PERSISTENT_PLATES:
            safe_plate_ids.append(getPlateId(plate, plates))
        safe_plate_ids = cleanList(safe_plate_ids)
        log.info("Safe plates found.\n")

        # New list that filters plates that are safe
        plates_to_delete = [
            plate for plate in all_plate_ids if plate not in safe_plate_ids]

        if plates_to_delete:
            log.info(plates_to_delete, plates)
            return 1  # Completed

        else:
            log.info("-------------------------------")
            log.info(
                "The organization has already been purged.\
There are no more plates to delete.")
            log.info("-------------------------------")

            return 1  # Completed
    else:
        log.warning("No plates were found.")

        return 1  # Copmleted


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    run()
