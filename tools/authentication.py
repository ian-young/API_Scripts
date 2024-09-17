"""
Author: Ian Young
Purpose: This script is used to log in and log out of a Command account.
"""

# Import essential libraries
from typing import Optional

# Third-party imports
import requests

# Import custom exceptions to save space
from tools.api_endpoints import LOGIN, LOGOUT
from tools.custom_exceptions import APIExceptionHandler
from tools.log import log
from tools.verkada_totp import generate_totp


def login_and_get_tokens(
    login_session: requests.Session,
    username: str,
    password: str,
    org_id: str,
    totp: Optional[str] = None,
) -> tuple[str, str, str]:
    """
    Logs in a user to the Verkada API using the provided session and
    credentials, and retrieves the session tokens.

    Args:
        login_session: The requests session to use for the login request.
        username: The username of the user.
        password: The password of the user.
        org_id: The organization ID for which the user is logging in.
        totp: The Time-based One-Time Password (TOTP) if two-factor
            authentication is enabled (optional).

    Returns:
        A tuple containing the CSRF token, user token, and user ID
        after successful login.

    Raises:
        APIExceptionHandler: If an error occurs during
        the login process.
    """

    # Prepare login data
    if totp:
        login_data = {
            "email": username,
            "password": password,
            "otp": generate_totp(totp),
            "org_id": org_id,
        }
    else:
        login_data = {
            "email": username,
            "password": password,
            "org_id": org_id,
        }

    try:
        # Request the user session
        log.debug("Requesting session.")
        response = login_session.post(LOGIN, json=login_data)
        response.raise_for_status()
        log.debug("Session opened.")

        # Extract relevant information from the JSON response
        log.debug("Parsing JSON response.")
        json_response = response.json()
        session_csrf_token = json_response.get("csrfToken")
        session_user_token = json_response.get("userToken")
        session_user_id = json_response.get("userId")
        log.debug("Response parsed. Returning values.")

        return session_csrf_token, session_user_token, session_user_id

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise APIExceptionHandler(e, response, "Log in") from e


def logout(
    logout_session: requests.Session,
    x_verkada_token: str,
    x_verkada_auth: str,
    org_id: str,
):
    """
    Logs out the user from the Verkada API using the provided session and
    authentication details.

    Args:
        logout_session: The requests session to use for the logout
            request.
        x_verkada_token: The Verkada token for authentication.
        x_verkada_auth: The Verkada user ID for authentication.
        org_id: The organization ID for which the user is logged in.

    Returns:
        None

    Raises:
        APIExceptionHandler: If an error occurs during
        the logout process.
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
        response.raise_for_status()

        log.info("Logging out.")

    # Handle exceptions
    except requests.exceptions.RequestException as e:
        raise APIExceptionHandler(e, response, "Logout") from e

    finally:
        logout_session.close()
