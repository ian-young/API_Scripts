# Author: Ian Young
# NOTE: comment out the globally defined API_KEY and uncomment the other API lines if
# you'd like to enter it manually each time you run the script.
import requests

# Globally defined variables
API_KEY = "vkd_api_356c542f37264c99a6e1f95cac15f6af"
URL = "https://api.verkada.com/cameras/v1/people/person_of_interest"


def getPersonID(org_id, label_to_search, api_key=API_KEY):
    """Accepts a string as a search value and returns the person id associated with it"""

    # Define request headers
    headers = {
        'accept': 'application/json',
        'x-api-key': api_key
    }

    # Define query parameters for the request
    params = {
        'org_id': org_id,
        'label': label_to_search
    }

    # Send a GET request to search for persons of interest
    response = requests.get(URL, headers=headers, params=params)

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
            print(f"No person was found with the label '{label_to_search}'.")
    else:
        print(
            f"Failed to retrieve persons of interest. Status code: {response.status_code}")


def updateName(person_id, newLabel, api_key=API_KEY):
    """Takes a person ID and a string and will change the label of the given PoI"""

    payload = {"label": newLabel}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": api_key
    }

    # Define query parameters for the request
    params = {
        'org_id': org_id,
        'person_id': person_id
    }

    response = requests.patch(
        URL, json=payload, headers=headers, params=params)

    if response.status_code == 200:
        print(f"Changed name to '{newLabel}'")
    else:
        print(f"Could not change '{person_id}' to '{newLabel}'.")


# Check if it is being ran directly or imported
if __name__ == "__main__":
    # Prompt for values; this allows for mass usage by running in a for loop
    org_id = str(input("Please enter the Org ID: "))
    search = str(input("What is the PoI label you'd like to change?\n "))
    newName = str(input("New label: "))
    # api_key = str(input("Org API key: "))

    pid = getPersonID(org_id, search)
    # pid = getPersonID(org_id, search, api_key)

    if pid:
        updateName(org_id, pid, newName)
        # updateName(org_id, search, api_key)
    else:
        print(f"Could not retrieve pid for 'newName'")
