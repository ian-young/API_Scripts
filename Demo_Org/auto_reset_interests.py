"""
Author: Ian Young
Purpose: Compare plates to a pre-defined array of names.
These names will be "persistent plates/persons" which are to remain in
Command. Any person or plate not marked thusly will be deleted from the org.
"""

# Import essential libraries
import threading
import time

from app.people import run_people
from app.plates import run_plates
from app import GPIO, RUN_PIN
from tools import log


##############################################################################
###################################  Main  ###################################
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    if GPIO:
        GPIO.output(RUN_PIN, True)

    start_time = time.time()
    PoI = threading.Thread(target=run_people)
    LPoI = threading.Thread(target=run_plates)

    # Start the threads running independently
    PoI.start()
    LPoI.start()

    # Join the threads back to parent process
    PoI.join()
    LPoI.join()
    elapsed_time = time.time() - start_time
    if GPIO:
        GPIO.output(RUN_PIN, False)

    log.info("Total time to complete: %.2fs", elapsed_time)
