"""
Author: Ian Young
Purpose: Practice authenticating into Command using user credentials in place
of an API key. The script can also be used to practice extracting useful data
from the response.
"""
# Import essential libraries
from os import getenv

import requests
from dotenv import load_dotenv

load_dotenv()  # Load credentials file

LOGIN_URL = "https://vprovision.command.verkada.com/user/login"
DASHBOARD_URL = "https://command.verkada.com/dashboard"
username = getenv("")
password = getenv("")
org_id = getenv("")

# Step 1: Send a POST request with login data
login_data = {
    "email": username,
    "password": password,
    "org_id": org_id,
}

try:

    with requests.Session() as session:
        response = session.post(LOGIN_URL, json=login_data)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

        # Extract CSRF token from the JSON response body
        csrf_token = response.json().get("csrfToken")

        # You can print or use csrf_token as needed
        print(f"CSRF Token: {csrf_token}")

        # Print the full response for further analysis
        # print("Response:", response.text)

        # Now you can use the 'session' object to make authenticated requests to other pages
        authenticated_response = session.get(DASHBOARD_URL)

        # Print the content of the authenticated page
        # print("Authenticated Page:", authenticated_response.text)

except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
    session.close()
