# Author: Ian Young
# This script will create a POI when given a name and file path to an image

import base64
import requests
import creds
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

# Globally-defined Verkada PoI URL
URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"
API_KEY = creds.lab_key
ORG_ID = creds.lab_id
IMAGE_PATH = "/Users/ian.young/Pictures/fake female.jpg"


def createPOI(name, org_id=ORG_ID, api_key=API_KEY):
    """
    Will create a person of interest with a given URL to an image or path to
a file.

    :param name: The label for the person of interest to be created.
    :type name: str
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: None
    :rtype: None
    """
    file_content = None  # Pre-define

    try:
        print(f"{Fore.LIGHTCYAN_EX}Reading file...")
        with open(IMAGE_PATH, "rb") as image_file:
            # Read the binary content
            file_content = image_file.read()

    except FileNotFoundError:
        print(f"{Fore.RED}Error:{Style.RESET_ALL} The path was not found.")

    except Exception as e:
        print(f"Couldn't run: {e}")

    if file_content is not None:
        print(f"{Fore.LIGHTCYAN_EX}Encoding file...")

        # Convert the binary content to base64
        base64_image = base64.b64encode(file_content).decode('utf-8')
        print(f"{Fore.LIGHTGREEN_EX}File encoded!")

        print(f"{Fore.LIGHTCYAN_EX}Calling API endpoint...")
        
        # Set payload
        payload = {
            "label": name,
            "base64_image": base64_image
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": api_key
        }

        params = {
            "org_id": org_id
        }

        response = requests.post(
            URL, json=payload, headers=headers, params=params)
        if response.status_code == 200:
            print(response.text)

        elif response.status_code == 504:
            print(f"{Fore.LIGHTRED_EX}Request timed out.")

        else:
            print(f"{Fore.RED}Failed:{Style.RESET_ALL} {response.status_code}")


# Check if the code is being ran directly or imported
if __name__ == "__main__":
    # key = str(input("API Key: "))
    # oid = str(input("Org ID: "))
    name = str(input("PoI label: "))

    createPOI(name)
