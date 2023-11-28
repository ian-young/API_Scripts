# Author: Ian Young
# This script will create a POI when given a name and uri to image

import base64, creds, logging, requests, threading, time

# Globally-defined Verkada PoI URL
URL_POI = "https://api.verkada.com/cameras/v1/people/person_of_interest"
URL_LPR = "https://api.verkada.com/cameras/v1/\
analytics/lpr/license_plate_of_interest"

ORG_ID = creds.lab_id
API_KEY = creds.lab_key

# This will help prevent exceeding the call limit
CALL_COUNT = 0
CALL_COUNT_LOCK = threading.Lock()

# Set logger
log = logging.getLogger()
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

# Define header and parameters for API requests
HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-api-key": API_KEY
}

PARAMS = {
    "org_id": ORG_ID
}


class APIThrottleException(Exception):
    """
    Exception raised when the API request rate limit is exceeded.

    :param message: A human-readable description of the exception.
    :type message: str
    """
    def __init__(self, message="API throttle limit exceeded."):
        self.message = message
        super.__init__(self.message)


def createPOI(name, image, download):
    """
    Will create a person of interest with a given URL to an image or path to a file
    
    :param name: The name of the person of interest to be created.
    :type name: str
    :param image: The URL to the image of the person of interest. This image
must be a portrait of a human.
    :type image: str
    :param download: A value of 'y' or 'n' to indicate whether the image needs
to be downloaded. Most cases, the value will be 'y.'
    :type download: str
    :return: None
    :rtype: None
    """
    global CALL_COUNT

    # Don't bother running if at throttle limit
    if CALL_COUNT >= 500:
        return
    
    file_content = None  # Pre-define

    if download == 'y':
        # Download the JPG file from the URL
        img_response = requests.get(image)

        if img_response.status_code == 200:
            # File was successfully downloaded
            file_content = img_response.content
        else:
            # Handle the case where the file download failed
            log.critical("Failed to download the image")
    else:
        file_content = image  # No need to parse the file

    # Convert the binary content to base64
    base64_image = base64.b64encode(file_content).decode('utf-8')

    # Set payload
    payload = {
        "label": name,
        "base64_image": base64_image
    }

    try:
        response = requests.post(
            URL_POI, json=payload, headers=HEADERS, params=PARAMS)
        
        with CALL_COUNT_LOCK:
            CALL_COUNT += 1

        if response.status_code == 429:
            raise APIThrottleException("API throttled")
        
        elif response.status_code != 200:
            log.warning(f"{response.status_code}: Could not create {name}")

    except APIThrottleException:
        log.critical("Hit API request rate limit of 500/min")


def createPlate(name, plate):
    """
    Create a LPoI with a given name and license plate number.

    :param name: This is the name that will be used for the description of the
license plate.
    :type name: str
    :param plate: The value of the license plate.
    :type plate: str
    :return: None
    :rtype: None
    """
    global CALL_COUNT

    # Don't even bother running if at the throttle limit
    if CALL_COUNT >= 500:
        return
    
    payload = {
        "description": name,
        "license_plate": plate
    }

    try:
        response = requests.post(
            URL_LPR, json=payload, headers=HEADERS, params=PARAMS)
        
        with CALL_COUNT_LOCK:
            CALL_COUNT += 1

        if response.status_code == 429:
            raise APIThrottleException("API throttled")
        elif response.status_code != 200:
            log.warning(f"{response.status_code}: Could not create {name}")
            log.warning(f"Response content: {response.text}")

    except APIThrottleException:
        log.critical("Hit API request rate limit of 500/min")
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")


# Check if the code is being ran directly or imported
if __name__ == "__main__":
    image = 'https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fi.\
pinimg.com%2F736x%2F87%2Fea%2F33%2F87ea336233db8ad468405db8f94da050--human-\
faces-photos-of.jpg&f=1&nofb=1&ipt=6af7ecf6cd0e15496e7197f3b6cb1527beaa8718\
c58609d4feca744209047e57&ipo=images'

    start_time = time.time()
    threads = []
    for i in range(1, 11):
        name = f'PoI{i}'
        plate = f'PLATE{i}'
        plate_name = f'Plate{i}'

        log.info(f"Running for {name} & {plate_name}")
        thread_poi = threading.Thread(
            target=createPOI, args=(name, image, 'y')
        )
        thread_poi.start()
        threads.append(thread_poi)

        thread_lpoi = threading.Thread(
            target=createPlate, args=(plate_name, plate)
        )
        thread_lpoi.start()
        threads.append(thread_lpoi)

    for thread in threads:
        thread.join()

    end_time = time.time()
    elapsed_time = end_time - start_time
    log.info(f"Time to complete: {elapsed_time}")

    print("\nComplete")
