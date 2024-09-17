"""
Author: Ian Young
Purpose: Compare users to a pre-defined array of names.
These names will be "persistent users" which are to remain in Command.
Any user not marked thusly will be deleted from the org.
"""

# Import essential libraries
from time import time

from app import GPIO, RUN_PIN
from app.users import run_users
from tools import log

##############################################################################
###################################  Main  ###################################
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    if GPIO:
        GPIO.output(RUN_PIN, True)

    start_time = time()

    run_users()

    elapsed_time = time() - start_time
    if GPIO:
        GPIO.output(RUN_PIN, False)

    log.info("Total time to complete: %.2fs", elapsed_time)
