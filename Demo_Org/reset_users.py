"""
Author: Ian Young
Purpose: Compare users to a pre-defined array of names.
These names will be "persistent users" which are to remain in Command.
Any user not marked thusly will be deleted from the org.
"""

# Import essential libraries
from app.users import print_name, purge, run_users
from app.config import PERSISTENT_USERS


##############################################################################
##################################  Users  ###################################
##############################################################################


# [ ] TODO: Add output to allow for use of this function
def warn():
    """Prints a warning message before continuing"""
    print("-------------------------------")
    print("WARNING!!!")
    print("Please make sure you have changed the persistent users variable.")
    print("Otherwise all of your users will be deleted.")
    print("Please double-check spelling, as well!")
    print("-------------------------------")
    cont = None
    while cont not in ["", " "]:
        cont = input("Press enter to continue\n")


def check_people(safe, to_delete, users, manager):
    """
    Checks with the user before continuing with the purge.

    :param safe: A list of people that are marked as safe.
    :type safe: list
    :param to_delete: A list of people to delete during the purge.
    :type to_delete: list
    :param persons: A list of all people found in the organization.
    :type persons: list
    :param manager: PurgeManager which indicates if the script should stop
    :type manager: PurgeManager
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
            safe_names = [print_name(user_id, users) for user_id in safe]
            persistent_names = PERSISTENT_USERS
            print_comparison(
                safe_names,
                persistent_names,
                "Please check that the two lists match:",
            )
            return get_confirmation("Do they match? (y/n) ")

        if level == "2":
            delete_names = [
                print_name(user_id, users) for user_id in to_delete
            ]
            print_comparison(
                delete_names, [], "Here are the persons being purged:"
            )
            return get_confirmation("Is this list accurate? (y/n) ")

        if level == "3":
            print("Good luck!")
            return True

        return False

    while True:
        print(
            "1. Check marked persistent persons against what the application found.\n"
            "2. Check what is marked for deletion by the application.\n"
            "3. Trust the process and blindly move forward."
        )

        trust_level = input("- ").strip()

        if trust_level in ["1", "2", "3"]:
            if handle_trust_level(trust_level):
                if trust_level in ["1", "2"]:
                    purge(to_delete, users, manager)
                return
        else:
            print("Invalid input. Please enter '1', '2', or '3'.")


##############################################################################
##################################  Main  ####################################
##############################################################################

# If the code is being ran directly and not imported.
if __name__ == "__main__":
    run_users()
