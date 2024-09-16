"""
Author: Ian Young
Purpose: Compare plates to a pre-defined array of names.
These names will be "persistent" which are to remain in Command.
Anything not marked thusly will be deleted from the org.
"""

import threading
from time import time

from app import run_people, run_plates
from app.users import run_users

from tools import log


##############################################################################
##################################  Misc  ####################################
##############################################################################


def warn():
    """Prints a warning message before continuing"""
    print("-------------------------------")
    print("WARNING!!!")
    print("Please make sure you have changed the persistent plates variable.")
    print("Otherwise all of your plates will be deleted.")
    print("Please double-check spelling, as well!")
    print("-------------------------------")
    cont = None

    while cont not in ["", " "]:
        cont = str(input("Press enter to continue")).strip()


##############################################################################
##################################  Main  ####################################
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    warn()

    poi_thread = threading.Thread(target=run_people)
    lpoi_thread = threading.Thread(target=run_plates)
    user_thread = threading.Thread(target=run_users)

    ANSWER = None
    RUN_USER, RUN_POI, RUN_LPOI = False, False, False

    while ANSWER not in ["y", "n"]:
        ANSWER = (
            str(input("Would you like to run for users?(y/n) "))
            .strip()
            .lower()
        )

        if ANSWER == "y":
            RUN_USER = True

    ANSWER = None
    while ANSWER not in ["y", "n"]:
        ANSWER = (
            str(input("Would you like to run for PoI?(y/n) ")).strip().lower()
        )

        if ANSWER == "y":
            RUN_POI = True

    ANSWER = None
    while ANSWER not in ["y", "n"]:
        ANSWER = (
            str(input("Would you like to run for LPoI?(y/n) ")).strip().lower()
        )

        if ANSWER == "y":
            RUN_LPOI = True

    # Time the runtime
    start_time = time()

    # Start threads
    if RUN_USER:
        user_thread.start()
    if RUN_POI:
        poi_thread.start()
    if RUN_LPOI:
        lpoi_thread.start()

    # Join back to main thread
    if RUN_USER:
        user_thread.join()
    if RUN_POI:
        poi_thread.join()
    if RUN_LPOI:
        lpoi_thread.join()

    # Wrap up in a bow and complete
    log.info("Time to complete: %.2fs.", time() - start_time)
    print("Exiting...")
