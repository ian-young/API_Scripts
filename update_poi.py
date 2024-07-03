"""
Author: Ian Young
NOTE: comment out the globally defined API_KEY and uncomment the other API lines if
you'd like to enter it manually each time you run the script.
"""

# Import essential libraries
from os import getenv

import requests
from dotenv import load_dotenv

load_dotenv()  # Load credentials file

# Globally defined variables
API_KEY = getenv("")
URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"


def get_person_id(target_org_id, label_to_search, api_key=API_KEY):
    """
    Accepts a string as a search value and returns the person id
    associated with it

    :param target_org_id: The id of the target Verkada organization.
    :type target_org_id: str
    :param label_to_search: The label of the person to search for.
    :type label_to_search: str
    :param api_key: The API key to authenticate with.
    :type api_key: str, optional
    :return: The person_id of the targeted PoI
    :rtype: str
    """

    # Define request headers
    headers = {"accept": "application/json", "x-api-key": api_key}

    # Define query parameters for the request
    params = {"org_id": target_org_id, "label": label_to_search}

    # Send a GET request to search for persons of interest
    response = requests.get(URL, headers=headers, params=params, timeout=5)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        if persons_of_interest := data.get("persons_of_interest", []):
            return persons_of_interest[0].get("person_id")
        else:
            print(f"No person was found with the label '{label_to_search}'.")
    else:
        print(
            f"Failed to retrieve persons of interest. Status code: {response.status_code}"
        )


def update_name(person_id, new_label, target_org_id, api_key=API_KEY):
    """
    Takes a person ID and a string and will change the label of the given
    PoI

    :param person_id: The id of the target Verkada PoI.
    :type person_id: str
    :param new_label: The new label name to update the PoI with.
    :type new_label: str
    :param target_org_id: The id of the target Verkada organization.
    :type target_org_id: str
    :param api_key: The API key used to authenticate.
    :type api_key: str, optional
    """

    payload = {"label": new_label}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": api_key,
    }

    # Define query parameters for the request
    params = {"org_id": target_org_id, "person_id": person_id}

    response = requests.patch(
        URL, json=payload, headers=headers, params=params, timeout=5
    )

    if response.status_code == 200:
        print(f"Changed name to '{new_label}'")
    else:
        print(f"Could not change '{person_id}' to '{new_label}'.")


# Check if it is being ran directly or imported
if __name__ == "__main__":
    # Prompt for values; this allows for mass usage by running in a for loop
    ORG_ID = str(input("Please enter the Org ID: "))
    SEARCH = str(input("What is the PoI label you'd like to change?\n "))
    NEWNAME = str(input("New label: "))
    if pid := get_person_id(ORG_ID, SEARCH):
        update_name(ORG_ID, pid, NEWNAME)
    else:
        print("Could not retrieve pid for 'newName'")
