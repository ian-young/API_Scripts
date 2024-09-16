"""
Author: Ian Young
Purpose: Interactive file to help clean a Verkada Command organization.
Compare plates to a pre-defined array of names.
These names will be "persistent plates" which are to remain in Command.
Any plate not marked thusly will be deleted from the org.
"""

# Import essential libraries
from app.plates import print_plate_name, purge_plates, run_plates
from app.config import PERSISTENT_PLATES


##############################################################################
#################################  PLates ####################################
##############################################################################


# [ ] TODO: Add output to allow for use of this function
def check_plates(safe, to_delete, license_plates):
    """
    Checks with the user before continuing with the purge.

    :param safe: A list of plates that are marked as safe.
    :type safe: list
    :param to_delete: A list of plates to delete during the purge.
    :type to_delete: list
    :param license_plates: A list of all plates found in the organization.
    :type license_plates: list
    """

    def print_comparison(list1, list2, title):
        print("-------------------------------")
        print(title)
        print(", ".join(list1))
        if list2:
            print("vs")
            print(", ".join(list2))
        print("-------------------------------")

    def get_confirmation(prompt):
        while True:
            response = input(prompt).strip().lower()
            if response in ["y", "n"]:
                return response == "y"
            print("Invalid input. Please enter 'y' or 'n'.")

    def handle_trust_level(level):
        if level == "1":
            safe_names = [
                print_plate_name(plate_id, license) for plate_id in safe
            ]
            persistent_names = PERSISTENT_PLATES
            print_comparison(
                safe_names,
                persistent_names,
                "Please check that the two lists match:",
            )
            return get_confirmation("Do they match? (y/n) ")

        if level == "2":
            delete_names = [
                print_plate_name(plate_id, license) for plate_id in to_delete
            ]
            print_comparison(
                delete_names, [], "Here are the plates being purged:"
            )
            return get_confirmation("Is this list accurate? (y/n) ")

        if level == "3":
            print("Good luck!")
            return True

        return False

    while True:
        print(
            "1. Check marked persistent plates against what the application found.\n"
            "2. Check what is marked for deletion by the application.\n"
            "3. Trust the process and blindly move forward."
        )

        trust_level = input("- ").strip()

        if trust_level in ["1", "2", "3"]:
            if handle_trust_level(trust_level):
                if trust_level in ["1", "2"]:
                    purge_plates(to_delete, license_plates)
                return
        else:
            print("Invalid input. Please enter '1', '2', or '3'.")


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
        cont = str(input("Press enter to continue\n")).strip()


##############################################################################
###################################  Main  ###################################
##############################################################################


# If the code is being ran directly and not imported.
if __name__ == "__main__":
    run_plates()
