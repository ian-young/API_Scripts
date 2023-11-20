# Author: Ian Young
# Purpose: Compare persons to a pre-defined array of names.
# These names will be "persistent persons" which are to remain in Command.
# Any person not marked thusly will be deleted from the org.

import creds, logging, requests, threading, time

ORG_ID = creds.lab_id
API_KEY = creds.lab_key

# Set logger
log = logging.getLogger()
logging.basicConfig(
    level = logging.INFO,
    format = "%(levelname)s: %(message)s"
    )

# Set the full name for which persons are to be persistent
PERSISTENT_PERSONS = ["PoI"]

URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"


def warn():
    """Prints a warning message before continuing"""
    print("-------------------------------")
    print("WARNING!!!")
    print("Please make sure you have changed the persistent persons variable.")
    print("Otherwise all of your persons will be deleted.")
    print("Please double-check spelling, as well!")
    print("-------------------------------")
    cont = None

    while cont not in ["", " "]:
        cont = str(input("Press enter to continue\n")).strip()


def check(safe, to_delete, persons):
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

            safe_names = [printName(person_id, persons) for person_id in safe]

            print(", ".join(safe_names))
            print("vs")
            print(", ".join(PERSISTENT_PERSONS))
            print("-------------------------------")

            while ok not in ['y', 'n']:
                ok = str(input("Do they match?(y/n) ")).strip().lower()

                if ok == 'y':
                    purge(to_delete, persons)

                elif ok == 'n':
                    print("Please check the input values")
                    print("Exiting...")

                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

        elif trust_level == '2':
            print("-------------------------------")
            print("Here are the persons being purged: ")

            delete_names = \
                [printName(person_id, persons) for person_id in to_delete]
            print(", ".join(delete_names))
            print("-------------------------------")

            while ok not in ['y', 'n']:
                ok = \
                    str(input("Is this list accurate?(y/n) ")).strip().lower()

                if ok == 'y':
                    purge(to_delete, persons)

                elif ok == 'n':
                    print("Please check the input values.")
                    print("Exiting...")

                else:
                    print("Invalud input. Please enter 'y' or 'n'.")

        elif trust_level == '3':
            print("Good luck!")
            purge(to_delete, persons)

        else:
            print("Invalid input. Please enter '1', '2', or '3'.")


def cleanList(list):
    """Removes any None values from error codes"""
    cleaned_list = [value for value in list if value is not None]
    return cleaned_list


def getPeople(org_id=ORG_ID, api_key=API_KEY):
    """Returns JSON-formatted persons in a Command org"""
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
        persons = data.get('persons_of_interest')
        return persons
    else:
        log.error(
            f"Error with retrieving persons.\
Status code {response.status_code}")
        return None


def getIds(persons=None):
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
        log.info(f"person {person} was not found in the database...")
        return None


def delete_person(person, persons, org_id=ORG_ID, api_key=API_KEY):
    """Deletes the given person"""
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }

    log.info(f"Running for person: {printName(person, persons)}")

    params = {
        'org_id': org_id,
        'person_id': person
    }

    response = requests.delete(URL, headers=headers, params=params)

    if response.status_code != 200:
        log.error(f"An error has occured. Status code {response.status_code}")
        return 2  # Completed unsuccesfully


def purge(delete, persons, org_id=ORG_ID, api_key=API_KEY):
    """Purges all PoIs that aren't marked as safe/persistent"""
    if not delete:
        log.warning("There's nothing here")
        return

    log.info("Purging...")

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

    print("Purge complete.")
    log.debug(f"Time to complete: {elapsed_time}")
    return 1  # Completed


def printName(to_delete, persons):
    """Returns the full name with a given ID"""
    person_name = None  # Pre-define

    for person in persons:
        if person.get('person_id') == to_delete:
            person_name = person.get('label')
            break  # No need to continue running once found

    if person_name:
        return person_name
    else:
        log.warning(f"person {to_delete} was not found in the database...")
        return "Error finding name"


def run():
    """Allows the program to be ran if being imported as a module"""
    # Uncomment the lines below if you want to manually set these values
    # each time the program is ran

    # org = str(input("Org ID: ""))
    # key = str(input("API key: "))

    warn()

    log.info("Retrieving persons")
    persons = getPeople()
    log.info("persons retrieved.\n")

    # Run if persons were found
    if persons:
        log.info("Gather IDs")
        all_person_ids = getIds(persons)
        all_person_ids = cleanList(all_person_ids)
        log.info("IDs aquired.\n")

        safe_person_ids = []

        log.info("Searching for safe persons.")
        # Create the list of safe persons
        for person in PERSISTENT_PERSONS:
            safe_person_ids.append(getPersonId(person, persons))
        safe_person_ids = cleanList(safe_person_ids)
        log.info("Safe persons found.\n")

        # New list that filters persons that are safe
        persons_to_delete = [
            person for person in all_person_ids if person not in safe_person_ids]

        if persons_to_delete:
            check(safe_person_ids, persons_to_delete, persons)
            return 1  # Completed

        else:
            log.info("-------------------------------")
            log.info(
                "The organization has already been purged.\
There are no more persons to delete.")
            log.info("-------------------------------")

            return 1  # Completed
    else:
        log.warning("No persons were found.")

        return 1  # Copmleted


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    run()

