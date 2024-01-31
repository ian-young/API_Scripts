# Author: Ian Young
# Purpose: Compare plates to a pre-defined array of names.
# These names will be "persistent plates/persons" which are to remain in 
# Command. Any person or plate not marked thusly will be deleted from the org.

import creds, datetime, logging, requests, threading, time

ORG_ID = creds.demo_id
API_KEY = creds.demo_key

# Set timeout for a 429
MAX_RETRIES = 10
DEFAULT_RETRY_DELAY = 0.25
BACKOFF = 0.25

# Set logger
log = logging.getLogger()
log.setLevel(logging.WARNING)
logging.basicConfig(
    level = logging.WARNING,
    format = "%(levelname)s: %(message)s"
    )

# Mute non-essential logging from requests library
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

try:
    import RPi.GPIO as GPIO  # type: ignore

    work_pin = 7
    lpoi_pin = 13
    poi_pin = 11

    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(work_pin, GPIO.OUT)
    except RuntimeError:
        GPIO = None
        log.debug("Runtime error while initializing GPIO boad.")
except ImportError:
    GPIO = None
    log.debug("RPi.GPIO is not availbale. Running on a non-Pi platform")

# Set the full name for which plates are to be persistent
PERSISTENT_PLATES = [""]
PERSISTENT_PERSONS = [""]

# Set API endpoint URLs
PLATE_URL = "https://api.verkada.com/cameras/v1/\
analytics/lpr/license_plate_of_interest"
PERSON_URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"


##############################################################################
                                #  Misc  #
##############################################################################


class RateLimiter:
    def __init__(self, rate_limit, max_events_per_sec=10, pacing=1):
        """
        Initilization of the rate limiter.

        :param rate_limit: The value of how many threads may be made each sec.
        :type rate_limit: int
        :param max_events_per_sec: Maximum events allowed per second.
        :type: int, optional
        :param pacing: Sets the interval of the clock in seconds.
        :type pacing: int, optional
        :return: None
        :rtype: None
        """
        self.rate_limit = rate_limit
        self.lock = threading.Lock()  # Local lock to prevent race conditions
        self.max_events_per_sec = max_events_per_sec
        self.pacing = pacing


    def acquire(self):
        """
        States whether or not the program may create new threads or not.

        :return: Boolean value stating whether new threads may be made or not.
        :rtype: bool
        """
        with self.lock:
            current_time = time.time()  # Define current time

            if not hasattr(self, 'start_time'):
                # Check if attribue 'start_time' exists, if not, make it.
                self.start_time = current_time
                self.event_count = self.pacing
                return True
            
            # How much time has passed since starting
            elapsed_time = current_time - self.start_time

            # Check if it's been less than 1sec and less than 10 events have
            # been made.
            if elapsed_time < self.pacing / self.rate_limit \
                and self.event_count < self.max_events_per_sec:
                self.event_count += 1
                return True
            
            # Check if it is the first wave of events
            elif elapsed_time >= self.pacing / self.rate_limit:
                self.start_time = current_time
                self.event_count = 2
                return True
            
            else:
                # Calculate the time left before next wave
                remaining_time = self.pacing - \
                    (current_time - self.start_time)
                time.sleep(remaining_time)  # Wait before next wave
                return True
            

class APIThrottleException(Exception):
    """
    Exception raised when the API request rate limit is exceeded.

    :param message: A human-readable description of the exception.
    :type message: str
    """
    def __init__(self, message="API throttle limit exceeded."):
        self.message = message
        super().__init__(self.message)


def run_thread_with_rate_limit(threads, rate_limit=10):
    """
    Run a thread with rate limiting.
        
    :param target: The target function to be executed in the thread:
    :type targe: function:
    :return: The thread that was created and ran
    :rtype: thread
    """
    limiter = RateLimiter(rate_limit=rate_limit)

    def run_thread(thread):
        with threading.Lock():
            limiter.acquire()
            log.debug(f"Starting thread {thread.name} at time \
{datetime.datetime.now().strftime('%H:%M:%S')}")
            thread.start()

    for thread in threads:
        run_thread(thread)

    for thread in threads:
        thread.join()


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


def flashLED(pin, local_stop_event, speed):
    """
    Flashes an LED that is wired into the GPIO board of a raspberry pi for
    the duration of work.

    :param pin: target GPIO pin on the board.
    :type pin: int
    :param local_stop_event: Thread-local event to indicate when the program's
    work is done and the LED can stop flashing.
    :type local_stop_event: Bool 
    :param speed: How long each flash should last in seconds.
    :type failed: int
    :return: None
    :rtype: None
    """
    while not local_stop_event.is_set():
        GPIO.output(pin, True)
        time.sleep(speed)
        GPIO.output(pin, False)
        time.sleep(speed * 2)


##############################################################################
                         #  All things people  #
##############################################################################


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

    if response.status_code == 200:
        data = response.json()  # Parse the response

        # Extract as a list
        persons = data.get('persons_of_interest')
        return persons
    else:
        log.critical(
            f"Person - Error with retrieving persons.\
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


def getPersonId(person=PERSISTENT_PERSONS, persons=None):
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
        log.warning(f"Person {person} was not found in the database...")
        return None


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
    local_data = threading.local()
    local_data.RETRY_DELAY = DEFAULT_RETRY_DELAY

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
        for _ in range(MAX_RETRIES):
            response = requests.delete(PERSON_URL, headers=headers, params=params)

            if response.status_code == 429:
                log.info(f"{printPersonName(person, persons)} response: 429. \
Retrying in {local_data.RETRY_DELAY}s.")
                
                time.sleep(local_data.RETRY_DELAY)

                local_data.RETRY_DELAY += BACKOFF

            else:
                break
    
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
    
    local_stop_event = threading.Event()

    if GPIO and poi_pin:
        flash_thread = threading.Thread(target=flashLED, args=(poi_pin, local_stop_event, 0.5))
        flash_thread.start()

    log.info("Person - Purging...")

    start_time = time.time()
    threads = []
    for person in delete:
        # Toss delete function into a new thread
        thread = threading.Thread(
            target=delete_person, args=(person, persons, org_id, api_key)
        )
        threads.append(thread)  # Add the thread to the pile

    run_thread_with_rate_limit(threads)

    end_time = time.time()
    elapsed_time = end_time - start_time

    log.info("Person - Purge complete.")
    log.info(f"Person - Time to complete: {elapsed_time:.2f}")

    if GPIO and poi_pin:
        local_stop_event.set()
        flash_thread.join()

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
            break  # No need to continue running once found

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
    log.info("Retrieving persons")
    persons = getPeople()
    log.info("persons retrieved.")

    # Run if persons were found
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
            purgePeople(persons_to_delete, persons)
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

    if response.status_code == 200:
        data = response.json()  # Parse the response

        # Extract as a list
        plates = data.get('license_plate_of_interest')
        return plates
    else:
        log.critical(
            f"Plate - Error with retrieving plates.\
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
                f"Plate - There has been an error with plate {plate.get('label')}.")

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
        log.error(f"Plate {plate} was not found in the database...")
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
    local_data = threading.local()
    local_data.RETRY_DELAY = DEFAULT_RETRY_DELAY

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
        for _ in range(MAX_RETRIES):
            response = requests.delete(PLATE_URL, headers=headers, params=params)

            if response.status_code == 429:
                log.info(f"{printPlateName(plate, plates)} response: 429. \
Retrying in {local_data.RETRY_DELAY}s.")
                
                time.sleep(local_data.RETRY_DELAY)

                local_data.RETRY_DELAY += BACKOFF

            else:
                break
    
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
    
    if not delete:
        log.warning("Plate - There's nothing here")
        return
    
    local_stop_event = threading.Event()

    if GPIO and poi_pin:
        flash_thread = threading.Thread(target=flashLED, args=(lpoi_pin, local_stop_event, 0.5))
        flash_thread.start()

    log.info("Plate - Purging...")

    start_time = time.time()
    threads = []
    for plate in delete:
        # Toss delete function into a new thread
        thread = threading.Thread(
            target=delete_plate, args=(plate, plates, org_id, api_key)
        )
        threads.append(thread)  # Add the thread to the pile

    run_thread_with_rate_limit(threads)

    end_time = time.time()
    elapsed_time = end_time - start_time

    log.info("Plate - Purge complete.")
    log.info(f"Plate - Time to complete: {elapsed_time:.2f}")

    if GPIO and poi_pin:
        local_stop_event.set()
        flash_thread.join()
    
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
        return "No name provided"


def runPlates():
    """
    Allows the program to be ran if being imported as a module.
    
    :return: Returns the value 1 if the program completed successfully.
    :rtype: int
    """
    log.info("Retrieving plates")
    plates = getPlates()
    log.info("Plates retrieved.")

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
    if GPIO:
        GPIO.output(work_pin, False)

    log.info(f"Total time to complete: {elapsed_time:.2f}") 
