"""
Author: Ian Young
This script will create a POI when given a name and uri to image
"""
# Import essential libraries
import base64
from os import getenv

import requests
from dotenv import load_dotenv

load_dotenv()  # Load credentials file

# Globally-defined Verkada PoI URL
URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"
API_KEY = getenv("lab_key")
ORG_ID = getenv("lab_id")


def create_poi(name, image, download, org_id=ORG_ID, api_key=API_KEY):
    """
        Will create a person of interest with a given URL to an image or path to a file.

        :param name: The label for the person of interest to be created.
        :type name: str
        :param image: the link to the portrait image of the person of interest.
        :type image: str
        :param download: A 'y' or 'n' value indicating whether the image link
    needs to be downloaded.
        :type: str
        :param org_id: Organization ID. Defaults to ORG_ID.
        :type org_id: str, optional
        :param api_key: API key for authentication. Defaults to API_KEY.
        :type api_key: str, optional
        :return: None
        :rtype: None
    """

    file_content = None  # Pre-define
    if download == "y":
        # Download the JPG file from the URL
        img_response = requests.get(image, timeout=5)

        if img_response.status_code == 200:
            # File was successfully downloaded
            file_content = img_response.content
        else:
            # Handle the case where the file download failed
            print("Failed to download the image")
    else:
        file_content = image  # No need to parse the file

    # Convert the binary content to base64
    base64_image = base64.b64encode(file_content).decode("utf-8")

    # Set payload
    payload = {"label": name, "base64_image": base64_image}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": api_key,
    }

    params = {"org_id": org_id}

    response = requests.post(
        URL, json=payload, headers=headers, params=params, timeout=5
    )

    print(response.text)


# Check if the code is being ran directly or imported
if __name__ == "__main__":
    NAME = str(input("PoI label: "))

    DOWNLOAD = ""  # Define before asking
    IMAGE = ""  # Define before asking
    # Loop until the user enters a valid response
    while DOWNLOAD not in ["y", "n"]:
        DOWNLOAD = (
            input("Will the image need to be downloaded?\n(y/n) ")
            .strip()
            .lower()
        )
        if DOWNLOAD == "y":
            print(
                "NOTE: The URL to the image and the webpage are two "
                "different things."
            )
            IMAGE = str(input("Please enter the URL to the image here: "))
        elif DOWNLOAD == "n":
            IMAGE = str(input("Path to the image: "))
        else:
            print("Invalid input. Please enter 'Y' or 'N'.")

    create_poi(NAME, IMAGE, DOWNLOAD)
