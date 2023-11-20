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


def check(safe, to_delete, plates):
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

            safe_names = [printName(plate_id, plates) for plate_id in safe]

            print(", ".join(safe_names))
            print("vs")
            print(", ".join(PERSISTENT_PLATES))
            print("-------------------------------")

            while ok not in ['y', 'n']:
                ok = str(input("Do they match?(y/n) ")).strip().lower()

                if ok == 'y':
                    purge(to_delete, plates)

                elif ok == 'n':
                    print("Please check the input values")
                    print("Exiting...")

                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

        elif trust_level == '2':
            print("-------------------------------")
            print("Here are the plates being purged: ")

            delete_names = \
                [printName(plate_id, plates) for plate_id in to_delete]
            print(", ".join(delete_names))
            print("-------------------------------")

            while ok not in ['y', 'n']:
                ok = \
                    str(input("Is this list accurate?(y/n) ")).strip().lower()

                if ok == 'y':
                    purge(to_delete, plates)

                elif ok == 'n':
                    print("Please check the input values.")
                    print("Exiting...")

                else:
                    print("Invalud input. Please enter 'y' or 'n'.")

        elif trust_level == '3':
            print("Good luck!")
            purge(to_delete)

        else:
            print("Invalid input. Please enter '1', '2', or '3'.")


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
        print(
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
            print(
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
        print(f"plate {plate} was not found in the database...")
        return None


def delete_plate(plate, plates, org_id=ORG_ID, api_key=API_KEY):
    """Deletes the given person"""
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    print(f"Running for plate: {printName(plate, plates)}")

    params = {
        'org_id': org_id,
        'license_plate': plate
    }

    response = requests.delete(URL, headers=headers, params=params)

    if response.status_code != 200:
        print(f"An error has occured. Status code {response.status_code}")
        return 2  # Completed unsuccesfully


def purge(delete, plates, org_id=ORG_ID, api_key=API_KEY):
    """Purges all PoIs that aren't marked as safe/persistent"""
    if not delete:
        print("There's nothing here")
        return

    print("\nPurging...")

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

    print("Purge complete.")
    logging.info(f"Time to complete: {elapsed_time}")
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
        print(f"plate {to_delete} was not found in the database...")
        return "Error finding name"


def run():
    """Allows the program to be ran if being imported as a module"""
    # Uncomment the lines below if you want to manually set these values
    # each time the program is ran

    # org = str(input("Org ID: ""))
    # key = str(input("API key: "))

    warn()

    print("Retrieving plates")
    plates = getPlates()
    print("plates retrieved.\n")

    # Run if plates were found
    if plates:
        print("Gather IDs")
        all_plate_ids = getIds(plates)
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
            check(safe_plate_ids, plates_to_delete, plates)
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


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    run()
