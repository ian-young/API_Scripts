# Author: Ian Young
# Purpose: Test Verkada API endpoints.
# This script is to be ran using the pip module pytest
# Anything that starts with test will be ran by pytest
# The script only looks for a 200 response code.
# WARNING:
# You might have a test PoI left in your org if the endpoint is not fixed

import requests
import base64

# Set URLs
URL_PEOPLE = "https://api.verkada.com/cameras/v1/people/person_of_interest"
URL_PLATE = "https://api.verkada.com/cameras/v1/analytics/lpr/license_plate\
_of_interest"
URL_CLOUD = "https://api.verkada.com/cameras/v1/cloud_backup/settings"
URL_OBJ = "https://api.verkada.com/cameras/v1/analytics/object_counts"
URL_MQTT = "https://api.verkada.com/cameras/v1/analytics/object_position_mqtt"
URL_OCCUPANCY = "https://api.verkada.com/cameras/v1/analytics/occupancy_trends"
URL_DEVICES = "https://api.verkada.com/cameras/v1/devices"
URL_FOOTAGE = "https://api.verkada.com/cameras/v1/footage/thumbnails/latest"
URL_AUDIT = "https://api.verkada.com/core/v1/audit_log"
URL_CORE = "https://api.verkada.com/core/v1/user"
URL_AC_GROUPS = "https://api.verkada.com/access/v1/access_groups"
URL_AC_USERS = "https://api.verkada.com/access/v1/access_users"
URL_AC_CRED = "https://api.verkada.com/access/v1/credentials/card"
URL_AC_PLATE = "https://api.verkada.com/access/v1/credentials/license_plate"

# Set general testing variables
ORG_ID = "16f37a49-2c89-4bd9-b667-a28af7700068"
API_KEY = "vkd_api_356c542f37264c99a6e1f95cac15f6af"
CAMERA_ID = "c94be2a0-ca3f-4f3a-b208-8db8945bf40b"
TEST_USER = "3339db66-f954-465c-ae59-e6686a8e9c3c"
TEST_USER_CRED = "d7a77639-e451-4d35-b18f-8fd8ae2cd0a6"
CARD_ID = "00111101100000100110100100"
PLATE = "H3LL0"

GENERAL_HEADER = {
    'accept': 'application/json',
    'x-api-key': API_KEY
}


##############################################################################
                                #  Test PoI  #
##############################################################################


def getPersonID():
    """Accepts a string as a search value and returns the person id\
 associated with it"""
    # Define query parameters for the request
    params = {
        'org_id': ORG_ID,
        'label': 'test'
    }

    # Send a GET request to search for persons of interest
    response = requests.get(URL_PEOPLE, headers=GENERAL_HEADER, params=params)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Extract the list of persons of interest
        persons_of_interest = data.get('persons_of_interest', [])

        if persons_of_interest:
            # Extract the person_id from the first (and only) result
            person_id = persons_of_interest[0].get('person_id')
            return person_id
            # print(f"Person ID for label '{label_to_search}': {person_id}")
        else:
            print(f"No person was found with the label 'test'.")
    else:
        print(
            f"Failed to retrieve persons of interest. Status code: \
{response.status_code}")


def test_CreatePOI():
    """Creates a PoI to test the API endpoint"""
    file_content = None  # Pre-define

    # Download the JPG file from the URL
    img_response = requests.get(
        'https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fi.pinimg\
.com%2F736x%2F87%2Fea%2F33%2F87ea336233db8ad468405db8f94da050--human-faces-\
photos-of.jpg&f=1&nofb=1&ipt=6af7ecf6cd0e15496e7197f3b6cb1527beaa8718c58609d4\
feca744209047e57&ipo=images')

    if img_response.status_code == 200:
        # File was successfully downloaded
        file_content = img_response.content
    else:
        # Handle the case where the file download failed
        print("Failed to download the image")

    # Convert the binary content to base64
    base64_image = base64.b64encode(file_content).decode('utf-8')

    # Set payload
    payload = {
        "label": 'test',
        "base64_image": base64_image
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY
    }

    params = {
        "org_id": ORG_ID
    }

    response = requests.post(
        URL_PEOPLE, json=payload, headers=headers, params=params)

    assert response.status_code == 200


def test_getPOI():
    """Looks to see if it can get PoIs"""
    params = {
        "org_id": ORG_ID
    }

    response = requests.get(URL_PEOPLE, headers=GENERAL_HEADER, params=params)

    assert response.status_code == 200


def test_UpdatePOI():
    """Tests the patch requests for the people endpoint"""
    payload = {"label": 'Test'}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY
    }

    # Define query parameters for the request
    params = {
        'org_id': ORG_ID,
        'person_id': getPersonID()
    }

    response = requests.patch(
        URL_PEOPLE, json=payload, headers=headers, params=params)

    assert response.status_code == 200


def test_DeletePOI():
    """Tests the delete request for the people endpoint"""
    headers = {
        "accept": "application/json",
        "x-api-key": API_KEY
    }

    params = {
        "org_id": ORG_ID,
        "person_id": getPersonID()
    }

    response = requests.delete(URL_PEOPLE, headers=headers, params=params)

    assert response.status_code == 200


##############################################################################
                                #  Test LPoI  #
##############################################################################


def test_CreatePlate():
    """Creates a LPoI to test the API endpoint"""
    # Set payload
    payload = {
        "description": 'test',
        "license_plate": 't3stpl4te'
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY
    }

    params = {
        "org_id": ORG_ID
    }

    response = requests.post(
        URL_PLATE, json=payload, headers=headers, params=params)

    assert response.status_code == 200


def test_getLPOI():
    """Looks to see if it can get LPoIs"""
    headers = {
        "accept": "application/json",
        "x-api-key": API_KEY
    }

    params = {
        "org_id": ORG_ID
    }

    response = requests.get(URL_PLATE, headers=headers, params=params)

    assert response.status_code == 200


def test_UpdateLPOI():
    """Tests the patch requests for the LPoI endpoint"""
    payload = {"description": 'Test'}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY
    }

    # Define query parameters for the request
    params = {
        'org_id': ORG_ID,
        'license_plate': "t3stpl4te"
    }

    response = requests.patch(
        URL_PLATE, json=payload, headers=headers, params=params)

    assert response.status_code == 200


def test_DeleteLPOI():
    """Tests the delete request for the LPoI endpoint"""
    params = {
        "org_id": ORG_ID,
        'license_plate': "t3stpl4te"
    }

    response = requests.delete(
        URL_PLATE, headers=GENERAL_HEADER, params=params)

    assert response.status_code == 200


##############################################################################
                                # Test Cameras #
##############################################################################


def test_getCloudSettings():
    """Tests to see if it can retrieve cloud backup settings for a camera"""
    params = {
        'org_id': ORG_ID,
        'camera_id': CAMERA_ID
    }

    response = requests.get(URL_CLOUD, headers=GENERAL_HEADER, params=params)

    assert response.status_code == 200


def test_getCounts():
    """Tests if it can get object counts from a camera"""
    params = {
        'org_id': ORG_ID,
        'camera_id': CAMERA_ID
    }

    response = requests.get(URL_OBJ, headers=GENERAL_HEADER, params=params)

    assert response.status_code == 200


def test_getTrends():
    """Tests if it can get trend counts from a camera"""
    params = {
        'org_id': ORG_ID,
        'camera_id': CAMERA_ID
    }

    response = requests.get(
        URL_OCCUPANCY, headers=GENERAL_HEADER, params=params)

    assert response.status_code == 200


def test_getCameraData():
    """Tests if it can get camera data on a given camera"""
    params = {
        'org_id': ORG_ID,
        'camera_id': CAMERA_ID
    }

    response = requests.get(
        URL_OCCUPANCY, headers=GENERAL_HEADER, params=params)

    assert response.status_code == 200


def test_getThumbed():
    """Tests if it can get a thumbnail from a camera"""
    params = {
        'org_id': ORG_ID,
        'camera_id': CAMERA_ID,
        'resolution': 'low-res'
    }

    response = requests.get(URL_FOOTAGE, headers=GENERAL_HEADER, params=params)

    assert response.status_code == 200


##############################################################################
                                # Test Core #
##############################################################################


def test_getAudit():
    """Tests the ability to retrieve audit logs"""
    params = {
        'org_id': ORG_ID,
        'page_size': '1'
    }
    response = requests.get(URL_AUDIT, headers=GENERAL_HEADER, params=params)


def test_updateUser():
    """Tests the ability to update a user"""
    payload = {
        'active': False
    }

    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'x-api-key': API_KEY
    }

    params = {
        'org_id': ORG_ID,
        'user_id': TEST_USER
    }

    response = requests.put(URL_CORE, json=payload,
                            headers=headers, params=params)

    assert response.status_code == 200


def test_getUser():
    """Tests the ability to retrieve information on a user"""
    params = {
        'org_id': ORG_ID,
        'user_id': TEST_USER
    }

    response = requests.get(URL_CORE, headers=GENERAL_HEADER, params=params)

    assert response.status_code == 200


##############################################################################
                            # Test Access Control #
##############################################################################


def test_getGroups():
    """Tests the ability to get AC Groups"""
    params = {
        'org_id': ORG_ID
    }

    response = requests.get(
        URL_AC_GROUPS, headers=GENERAL_HEADER, params=params)

    assert response.status_code == 200


def test_getACUsers():
    """Tests the ability to get AC users"""
    params = {
        'org_id': ORG_ID
    }

    response = requests.get(
        URL_AC_USERS, headers=GENERAL_HEADER, params=params)

    assert response.status_code == 200


def test_changeCards():
    """Tests the ability to change credentials"""
    params = {
        'org_id': ORG_ID,
        'user_id': TEST_USER_CRED,
        'card_id': CARD_ID
    }

    activate_url = URL_AC_CRED + '/activate'
    deactivate_url = URL_AC_CRED + '/deactivate'

    active_response = requests.put(
        activate_url, headers=GENERAL_HEADER, params=params
    )

    deactive_response = requests.put(
        deactivate_url, headers=GENERAL_HEADER, params=params
    )

    codes = int(active_response.status_code)\
    + int(deactive_response.status_code)

    assert codes == 400

def test_changePlates():
    """Tests the ability to change access plates"""
    params = {
        'org_id': ORG_ID,
        'user_id': TEST_USER_CRED,
        'license_plate_number': PLATE
    }

    activate_url = URL_AC_PLATE + '/activate'
    deactivate_url = URL_AC_PLATE + '/deactivate'

    active_response = requests.put(
        activate_url, headers=GENERAL_HEADER, params=params
    )

    deactive_response = requests.put(
        deactivate_url, headers=GENERAL_HEADER, params=params
    )

    codes = int(active_response.status_code)\
    + int(deactive_response.status_code)

    assert codes == 400
