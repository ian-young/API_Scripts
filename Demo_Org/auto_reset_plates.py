"""
Author: Ian Young
Purpose: Compare plates to a pre-defined array of names.
These names will be "persistent plates/persons" which are to remain in
Command. Any person or plate not marked thusly will be deleted from the org.
"""

# Import essential libraries
import threading
import time

from app import GPIO, run_plates, RUN_PIN
from tools import log


##############################################################################
###################################  Main  ###################################
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    if GPIO:
        GPIO.output(RUN_PIN, True)

    start_time = time.time()
    LPoI = threading.Thread(target=run_plates)

    # Start the threads running independently
    LPoI.start()

    # Join the threads back to parent process
    LPoI.join()
    elapsed_time = time.time() - start_time
    if GPIO:
        GPIO.output(RUN_PIN, False)

    log.info("Total time to complete: %.2fs", elapsed_time)
