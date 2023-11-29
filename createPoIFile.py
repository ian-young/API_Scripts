# Author: Ian Young
# This script will create a POI when given a name and file path to an image

import base64
import creds
import colorama
from colorama import Fore, Style
import requests
import threading

colorama.init(autoreset=True)

# Globally-defined Verkada PoI URL
URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"
API_KEY = creds.lab_key
ORG_ID = creds.lab_id
IMAGE_PATH = "/Users/ian.young/Pictures/thispersondoesnotexist2.jpg"
CALL_COUNT = 0
CALL_COUNT_LOCK = threading.Lock()

# Each file name must be on a new line. File name format is expected to be
# the student's name then .jpg or whatever the format is. The file MUST be
# in the same directory of the script.
PATH_LIST = "test.txt"


def createPOI(name, path=IMAGE_PATH, org_id=ORG_ID, api_key=API_KEY):
    """
    Will create a person of interest with a given URL to an image or path to
a file.

    :param name: The label for the person of interest to be created.
    :type name: str
    :param path: Expected to be the name of an image that resides in the same
directory of the script being ran.
    :type path: str
    :param org_id: Organization ID. Defaults to ORG_ID.
    :type org_id: str, optional
    :param api_key: API key for authentication. Defaults to API_KEY.
    :type api_key: str, optional
    :return: None
    :rtype: None
    """
    global CALL_COUNT
    if CALL_COUNT >= 500:
        print("Hit API call limit of 500/min.")
        return

    file_content = None  # Pre-define

    try:
        with open(path, "rb") as image_file:
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
        
        with CALL_COUNT_LOCK:
            CALL_COUNT += 1

        if response.status_code == 200:
            print(f"{name} successfully created.")

        elif response.status_code == 504:
            print(f"{Fore.LIGHTRED_EX}Request timed out.")

        elif response.status_code == 400:
            print(f"{Fore.RED}Failed 400. Check image quality.")

        else:
            print(f"{Fore.RED}Failed:{Style.RESET_ALL} \
{response.status_code}")


# Check if the code is being ran directly or imported
if __name__ == "__main__":
    threads = []
    try:
        print(f"{Fore.LIGHTCYAN_EX}Reading file...")
        file = open(PATH_LIST, 'r')
        lines = file.readlines()

        for line in lines:
            if CALL_COUNT >= 500:
                break

            #print(f"{line.split('.')[0]}, {line.strip()}")
            new_thread = threading.Thread(target=createPOI,
                                    args=(line.split('.')[0], line.strip()))
            threads.append(new_thread)
            new_thread.start()

        for thread in threads:
            thread.join()

    except FileNotFoundError:
        print(f"{Fore.RED}File {PATH_LIST} not found.")
    
    except Exception as e:
        print(f"{Fore.RED}Couldn't run:{Style.RESET_ALL} {e}")