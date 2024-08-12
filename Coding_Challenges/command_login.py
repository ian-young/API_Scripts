"""
Author: Ian Young
Purpose: Practice authenticating into Command using user credentials in place
of an API key. The script can also be used to practice extracting useful data
from the response.
"""

# Import essential libraries
from os import getenv, environ

import requests
from dotenv import load_dotenv

from QoL.api_endpoints import DASHBOARD_URL, LOGIN

environ.clear()
load_dotenv()  # Load credentials file

username = getenv("")
password = getenv("")
org_id = getenv("")
if totp := getenv(""):
    login_data = {
        "email": username,
        "password": password,
        "otp": totp,
        "org_id": org_id,
    }
else:
    login_data = {
        "email": username,
        "password": password,
        "org_id": org_id,
    }

try:
    with requests.Session() as session:
        response = session.post(LOGIN, json=login_data)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

        # Extract CSRF token from the JSON response body
        csrf_token = response.json().get("csrfToken")

        # You can print or use csrf_token as needed
        print(f"CSRF Token: {csrf_token}")

        # Print the full response to view loaded results
        print("Response:", response.text)

        # Now you can use the 'session' object to make authenticated requests to other pages
        authenticated_response = session.get(DASHBOARD_URL)

        # Print the content of the authenticated page
        print("--------\nAuthenticated Page:", authenticated_response.text)

except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
    session.close()
