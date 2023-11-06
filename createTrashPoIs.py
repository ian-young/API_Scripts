# Author: Ian Young
# This script will create a POI when given a name and uri to image

import base64
import requests

# Globally-defined Verkada PoI URL
URL_POI = "https://api.verkada.com/cameras/v1/people/person_of_interest"
URL_LPR = "https://api.verkada.com/cameras/v1/analytics/lpr/license_plate_of_interest"

API_KEY = "vkd_api_356c542f37264c99a6e1f95cac15f6af"
ORG_ID = "16f37a49-2c89-4bd9-b667-a28af7700068"

# Define header and parameters for API requests
HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-api-key": API_KEY
}

PARAMS = {
    "org_id": ORG_ID
}


def createPOI(name, image, download):
    """Will create a person of interest with a given URL to an image or path to a file"""
    file_content = None  # Pre-define

    if download == 'y':
        # Download the JPG file from the URL
        img_response = requests.get(image)

        if img_response.status_code == 200:
            # File was successfully downloaded
            file_content = img_response.content
        else:
            # Handle the case where the file download failed
            print("Failed to download the image")
    else:
        file_content = image  # No need to parse the file

    # Convert the binary content to base64
    base64_image = base64.b64encode(file_content).decode('utf-8')

    # Set payload
    payload = {
        "label": name,
        "base64_image": base64_image
    }

    response = requests.post(
        URL_POI, json=payload, headers=HEADERS, params=PARAMS)

    if response.status_code != 200:
        print(f"{response.status_code}: Could not create {name}")


def createLPOI(name, plate):
    """Create a LPoI with a given name and plate"""
    payload = {
        'description': name,
        'license_plate': plate
    }

    response = requests.post(URL_LPR, json=payload, headers=HEADERS,
                             params=PARAMS)

    if response.status_code != 200:
        print(f"Something went wrong while creating {name}.")
        print(f"Status Code {response.status_code}")


# Check if the code is being ran directly or imported
if __name__ == "__main__":
    image = 'https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fi.\
pinimg.com%2F736x%2F87%2Fea%2F33%2F87ea336233db8ad468405db8f94da050--human-\
faces-photos-of.jpg&f=1&nofb=1&ipt=6af7ecf6cd0e15496e7197f3b6cb1527beaa8718\
c58609d4feca744209047e57&ipo=images'
    for i in range(1, 11):
        name = f'PoI{i}'
        plate = f'a{i}b{i}c{i}'
        plate_name = f'Plate{i}'

        print(f"Running for {name} & {plate_name}")
        createPOI(name, image, 'y')
        createLPOI(plate_name, plate)

    print("\nComplete")
