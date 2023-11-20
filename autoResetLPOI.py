# Author: Ian Young
# Purpose: Compare plates to a pre-defined array of names.
# These names will be "persistent plates" which are to remain in Command.
# Any plate not marked thusly will be deleted from the org.

import creds, logging, threading, requests, threading, time

ORG_ID = creds.lab_id
API_KEY = creds.lab_key

# Set the full name for which plates are to be persistent
PERSISTENT_PLATES = ["Random"]

URL = "https://api.verkada.com/cameras/v1/\
analytics/lpr/license_plate_of_interest"


def cleanList(list):
    """Removes any None values from error codes"""
    cleaned_list = [value for value in list if value is not None]
    return cleaned_list


def getPlates(org_id=ORG_ID, api_key=API_KEY):
    """Returns JSON-formatted plates in a Command org"""
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
        logging.error(
            f"Error with retrieving plates.\
Status code {response.status_code}")
        return None


def getIds(plates=None):
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
        logging.critical(f"plate {plate} was not found in the database...")
        return None


def delete_plate(plate, plates, org_id=ORG_ID, api_key=API_KEY):
    """Deletes the given person"""
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    logging.info(f"Running for plate: {printName(plate, plates)}")

    params = {
        'org_id': org_id,
        'license_plate': plate
    }

    response = requests.delete(URL, headers=headers, params=params)

    if response.status_code != 200:
        logging.error(
            f"An error has occured. Status code {response.status_code}")
        return 2  # Completed unsuccesfully


def purge(delete, plates, org_id=ORG_ID, api_key=API_KEY):
    """Purges all PoIs that aren't marked as safe/persistent"""
    if not delete:
        logging.warning("There's nothing here")
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


def printName(to_delete, plates):
    """Returns the full name with a given ID"""
    plate_name = None  # Pre-define

    for plate in plates:
        if plate.get('license_plate') == to_delete:
            plate_name = plate.get('description')
            break  # No need to continue running once found

    if plate_name:
        return plate_name
    else:
        logging.critical(f"\
plate {to_delete} was not found in the database...")
        return "Error finding name"


def run():
    """Allows the program to be ran if being imported as a module"""
    logging.info("Retrieving plates")
    plates = getPlates()
    logging.info("plates retrieved.\n")

    # Run if plates were found
    if plates:
        logging.info("Gather IDs")
        all_plate_ids = getIds(plates)
        all_plate_ids = cleanList(all_plate_ids)
        logging.info("IDs aquired.\n")

        safe_plate_ids = []

        # Create the list of safe plates
        logging.info("Searching for safe plates.")
        for plate in PERSISTENT_PLATES:
            safe_plate_ids.append(getPlateId(plate, plates))
        safe_plate_ids = cleanList(safe_plate_ids)
        logging.info("Safe plates found.\n")

        # New list that filters plates that are safe
        plates_to_delete = [
            plate for plate in all_plate_ids if plate not in safe_plate_ids]

        if plates_to_delete:
            logging.info(plates_to_delete, plates)
            return 1  # Completed

        else:
            logging.info("-------------------------------")
            logging.info(
                "The organization has already been purged.\
There are no more plates to delete.")
            logging.info("-------------------------------")

            return 1  # Completed
    else:
        logging.warning("No plates were found.")

        return 1  # Copmleted


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    run()
