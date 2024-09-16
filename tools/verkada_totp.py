"""
Author: Ian Young
Purpose: Generates a TOTP code.

Returns:
    int: A 6-digit TOTP that changes every 30 seconds.
"""

import time
from os import getenv, environ
import pyotp
from dotenv import load_dotenv

environ.clear()  # Clear any previously loaded variables
load_dotenv()  # Load new variables


def generate_totp(secret):
    """Generates a TOTP that from a given base32 secret

    Args:
        secret (str): A base32 encoded secret.

    Returns:
        int: A 6-digit TOTP
    """
    # Create a TOTP object with the provided secret
    totp = pyotp.TOTP(secret)
    # Generate the current TOTP code
    return totp.now()


# Run directly if not being imported as a module
if __name__ == "__main__":
    # Replace this with your own base32-encoded secret
    TOTP_SECRET = getenv("totp_secret")

    print(f"Secret: {TOTP_SECRET}")
    try:
        for _ in range(2):
            CURRENT_TOTP = generate_totp(TOTP_SECRET)
            print(f"Current TOTP: {CURRENT_TOTP}")
            # TOTP codes change every 30 seconds
            time.sleep(5)  # Run after 5 seconds in case it changed
    except KeyboardInterrupt:
        print("\nLeaving program.")
