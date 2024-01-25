import requests
from bs4 import BeautifulSoup
import creds

login_url = "https://vprovision.command.verkada.com/user/login"
dashboard_url = "https://command.verkada.com/dashboard"
username = creds.mc_u
password = creds.mc_p
org_id = creds.mc_oid

# Step 1: Send a POST request with login data
login_data = {
    "email": username,
    "password": password,
    "org_id": org_id,
}

try:

    with requests.Session() as session:
        response = session.post(login_url, json=login_data)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

        # Extract CSRF token from the JSON response body
        csrf_token = response.json().get("csrfToken")

        # You can print or use csrf_token as needed
        print(f"CSRF Token: {csrf_token}")

        # Print the full response for further analysis
        # print("Response:", response.text)

        # Now you can use the 'session' object to make authenticated requests to other pages
        authenticated_response = session.get(dashboard_url)

        # Print the content of the authenticated page
        # print("Authenticated Page:", authenticated_response.text)

except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
    session.close()