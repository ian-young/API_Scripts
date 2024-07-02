"""
Author: Ian Young
Purpose: Generates a TOTP code.

Returns:
    int: A 6-digit TOTP that changes every 30 seconds.
"""
import time
import base64
from os import getenv
import pyotp
from dotenv import load_dotenv

load_dotenv()

def string_to_base32(string):
    """
Converts a string to base32 encoding.

Args:
    string (str): The input string to be converted to base32.

Returns:
    str: The input string converted to base32 encoding as a UTF-8 decoded string.
"""

    # Encode the input string to bytes
    encoded_string = string.encode('utf-8')
    # Encode the bytes to base32
    encoded_base32 = base64.b32encode(encoded_string)

    return encoded_base32.decode('utf-8')

def generate_totp(secret):
    """Generates a TOTP that from a given base32 secret

    Args:
        secret (str): A base32 encoded secret.

    Returns:
        int: a 6-digit TOTP
    """
    # Create a TOTP object with the provided secret
    totp = pyotp.TOTP(secret)
    # Generate the current TOTP code
    return totp.now()

# Run directly if not being imported as a module
if __name__ == "__main__":
    # Replace this with your own base32-encoded secret
    TOTP_SECRET = string_to_base32(getenv("lab_password"))
    try:
        while True:
            CURRENT_TOTP = generate_totp(TOTP_SECRET)
            print(f"Current TOTP: {CURRENT_TOTP}")
            # TOTP codes change every 30 seconds
            time.sleep(30)
    except KeyboardInterrupt:
        print("Leaving program.")
