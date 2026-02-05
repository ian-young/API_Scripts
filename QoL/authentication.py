"""
Author: Ian Young
Purpose: This script is used to log in and log out of a Command account.
"""

# Import essential libraries
import logging
from os import getenv
from typing import Optional
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv, set_key, find_dotenv

# Import custom exceptions to save space
import QoL.custom_exceptions as custom_exceptions
from QoL.api_endpoints import LOGIN, LOGOUT
from QoL.verkada_totp import generate_totp

# Set up the logger
log = logging.getLogger()
LOG_LEVEL = logging.ERROR
log.setLevel(LOG_LEVEL)
logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s: %(message)s")


def get_api_token(key):
    """
    Retrieves an API token by checking the .env file first.
    If a cached token is less than 25 minutes old, it is returned.
    Otherwise, a new token is requested from the API and saved to .env.

    Args:
        key (str): The API key used for authentication.

    Returns:
        str: The API token.

    Raises:
        custom_exceptions.APIExceptionHandler: If an error occurs 
            during token generation.
    """
    # Locate and load the .env file
    env_file = find_dotenv()
    load_dotenv(env_file)

    # Retrieve cached values
    cached_token = getenv("TOKEN")
    timestamp_str = getenv("TOKEN_TIMESTAMP")
    
    # Check if we can use the cached token
    if cached_token and timestamp_str:
        try:
            last_generated = datetime.fromisoformat(timestamp_str)
            token_age = datetime.now() - last_generated
            
            # If token is younger than 25 minutes, return it
            if token_age < timedelta(minutes=25):
                log.info("Using valid cached API token.")
                log.debug(f"Cached token age: {token_age.seconds // 60} minutes.")
                return cached_token
            else:
                log.debug(f"Cached token expired. Age: {token_age.seconds // 60} minutes.")
                
        except ValueError:
            log.warning("Could not parse token timestamp. Refreshing token.")

    # If we are here, we need a new token
    log.info("Generating new API token...")
    headers = {"accept": "application/json", "x-api-key": key}

    try:
        response = requests.post(
            "https://api.verkada.com/token", headers=headers, timeout=5
        )
        response.raise_for_status()
        log.debug(f"Token generation response code: {response.status_code}")
        
        new_token = response.json()["token"]
        
        # Save the new token and current time to .env
        # Note: This writes physically to the file defined in env_file
        if env_file:
            set_key(env_file, "TOKEN", new_token)
            set_key(env_file, "TOKEN_TIMESTAMP", datetime.now().isoformat())
            log.info("New API token retrieved and saved to .env.")
        else:
            log.warning("No .env file found. Token will not be cached.")

        return new_token

    except requests.exceptions.RequestException as e:
        log.error(f"Failed to generate API token: {str(e)}")
        raise custom_exceptions.APIExceptionHandler(
            e, response if 'response' in locals() else None, "Get Token"
        ) from e


def login_and_get_tokens(
    login_session: requests.Session,
    username: str,
    password: str,
    org_id: str,
    org_name: str,
    totp: Optional[str] = None,
) -> tuple[str, str, str]:
    """
    Logs in a user to the Verkada API using the provided session and 
        credentials, and retrieves the session tokens.

    Args:
        login_session (requests.Session): The requests session used
            for the login request.
        username (str): The username of the user.
        password (str): The password of the user.
        org_id (str): The organization ID for which the user is
            logging in.
        org_name (str): The name of the organization.
        totp (Optional[str]): The Time-based One-Time Password (TOTP)
        if two-factor authentication is enabled.

    Returns:
        tuple[str, str, str]: A tuple containing the CSRF token, user
            token, and user ID after successful login.

    Raises:
        custom_exceptions.APIExceptionHandler: If an error occurs
            during the login process.
    """
    # 1. Set Browser Headers
    if "User-Agent" not in login_session.headers:
        log.debug("Setting default browser User-Agent headers.")
        login_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) \
                AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://command.verkada.com/",
            "Origin": "https://command.verkada.com"
        })

    try:
        # Step 0: Prime Session
        log.info("Priming session...")
        login_session.get("https://command.verkada.com/login")
        
        csrf_cookie = None
        for cookie in login_session.cookies:
            if "csrf" in cookie.name.lower():
                csrf_cookie = cookie.value
                break
        
        if csrf_cookie:
            log.debug("CSRF cookie found in priming session.")
            login_session.headers.update({"X-CSRF-Token": csrf_cookie})
        else:
            log.debug("No CSRF cookie found during priming session.")

        # Step 1: Login
        login_url = f"https://vprovision.command.verkada.com/__v/{org_name}/user/login"
        login_data = {
            "email": username,
            "password": password,
            "orgId": org_id,         
            "termsAcked": True,      
            "rememberMe": True,
            "shard": "prod1"         
        }
        if totp:
            log.debug("TOTP key provided; generating OTP for payload.")
            login_data["otp"] = generate_totp(totp)

        log.debug(f"Authenticating user: {username}...")
        log.debug(f"Authenticating via vprovision: {login_url}")
        response = login_session.post(login_url, json=login_data)
        
        # Check status before parsing to log specific errors if needed
        log.debug(f"Login HTTP Response: {response.status_code}")
        response.raise_for_status()
        
        # 1. Parse the JSON body immediately
        data = response.json()
        log.debug(f"response data: {data}")
        
        # 2. EXTRACT THE UUID TOKEN
        # The curl shows the cookie is named 'token', not 'verkada_token'
        uuid_token = login_session.cookies.get("token") 
        
        # If not in the jar, check if it was just set in response headers manually
        if not uuid_token:
            # Fallback for some environments
            uuid_token = login_session.cookies.get("verkada_token")

        if not uuid_token:
            log.critical("❌ Login succeeded but NO UUID COOKIE ('token') found.")
            log.critical(f"Cookies in jar: {login_session.cookies.get_dict()}")
        else:
            log.info(f"✅ Captured Session UUID: {uuid_token}")

        # 3. Setup Headers for subsequent requests
        # The 'x-verkada-token' header MUST be the UUID, not the v2 token.
        login_session.headers.update({
            "x-verkada-token": uuid_token,
            "x-verkada-organization-id": org_id,
            "X-CSRF-Token": data.get("csrfToken")
        })

        # Return the UUID as the main token
        return data.get("csrfToken"), uuid_token, data.get("userId")

    except requests.exceptions.RequestException as e:
        log.error(f"Authentication failed: {str(e)}")
        raise custom_exceptions.APIExceptionHandler(
            e, locals().get('response', None), "Log in"
        ) from e


def logout(
    logout_session: requests.Session,
    x_verkada_token: str,
    x_verkada_auth: str,
    org_id: str,
):
    """
    Logs out a user from the Verkada API using the provided session
        and authentication details.

    Args:
        logout_session (requests.Session): The requests session used
            for the logout request.
        x_verkada_token (str): The Verkada token for authentication.
        x_verkada_auth (str): The Verkada user ID for authentication.
        org_id (str): The organization ID for which the user is logged in.

    Returns:
        None

    Raises:
        custom_exceptions.APIExceptionHandler: If an error occurs 
            during the logout process.
    log.info("Initiating logout sequence...")
    """
    headers = {
        "X-Verkada-Organization-Id": org_id,
        "X-Verkada-Token": x_verkada_token,
        "X-Verkada-User-Id": x_verkada_auth,
        "content-type": "application/json",
    }

    body = {"logoutCurrentEmailOnly": True}
    try:
        response = logout_session.post(LOGOUT, headers=headers, json=body)
        log.debug(f"Logout HTTP Response: {response.status_code}")
        response.raise_for_status()

        log.info("Logout successful.")

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        log.error(f"Logout failed: {str(e)}")
        raise custom_exceptions.APIExceptionHandler(
            e, response, "Logout"
        ) from e

    finally:
        logout_session.close()
        log.debug("Session closed.")
