"""
Author: Ian Young
Purpose: This script will compare three csvs and generate a fourth with
    access users that are in the old system and sis but not in Command.
"""

import concurrent.futures
import csv
import gc
import logging
import re
import threading
from sys import stdout
from os import getpid
from typing import Dict, List, Optional, Union, TextIO

from tqdm import tqdm

from QoL.verbose_compute import memory_usage

PID = getpid()
IS_INTERACTIVE = stdout.isatty()

CSV_OUTPUT = "formatted_users.csv"
CSV_AC_LIST = "LegacySystemExport.csv"
CSV_SIS_USERS = "SISExport.csv"
CSV_CURRENT_USERS = "CurrentExport.csv"
CARD_TYPE = "Standard 26-bit Wiegand"
DOMAIN = "@email.com"
STATUS = "Active"

SCHOOL_ID_MAPPING = {
    "704": "(HS)",
    "304": "(JHS)",
    "114": "(ES)",
    "110": "(ESS)",
    "112": "(ESSS)",
}

calculate_memory = lambda start_mem, end_mem: end_mem - start_mem

# Clear all handlers associated with the root logger object
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

log = logging.getLogger()
LOG_LEVEL = logging.ERROR
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
    datefmt="%H:%M%S",
)
log.setLevel(LOG_LEVEL)


def count_lines(file_path: str) -> int:
    """
    Count the number of lines in a file.

    Args:
        file_path (str): The path to the file to count the lines in.

    Returns:
        int: The total number of lines in the file.

    Raises:
        This function does not raise any exceptions.
    """
    with open(file_path, "r", newline="", encoding="UTF-8") as count_file:
        return sum(1 for _ in count_file) - 1


def read_ac_csv(file_name: str) -> List[Dict[str, str]]:
    """
    Reads a CSV file and extracts the first name, last name, and email
        columns.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        list of dict: A list of dictionaries containing 'first_name',
            'last_name', and 'email'.
    """
    start_mem = memory_usage(PID)
    data: List[Dict[str, str]] = []

    # Open file
    with open(file_name, mode="r", newline="", encoding="UTF-8") as csv_file:
        # Set reader
        csv_reader = csv.DictReader(csv_file)

        log.info("Parsing access control csv")

        # Wrap in tqdm if being ran interactively
        iterator = (
            tqdm(csv_reader, total=count_lines(file_name), desc="Read AC File")
            if IS_INTERACTIVE
            else csv_reader
        )

        if not hasattr(iterator, "__iter__"):
            raise ValueError("read_ac_csv iterator is not iterable.")

        for row in iterator:
            # Extract useful columns
            name_parts = row["Name"].split(", ")
            if len(name_parts) == 2:
                data.append(
                    {
                        "First Name": name_parts[1],
                        "Last Name": name_parts[0],
                        "Card Number": row["cardNumber"],
                    }
                )
            else:
                data.append(
                    {
                        "First Name": name_parts[0],
                        "Last Name": "",
                        "Card Number": row["cardNumber"],
                    }
                )
    log.info("Data retrieved")
    log.debug(
        "Total memory used: %iKiB",
        calculate_memory(start_mem, memory_usage(PID)),
    )

    csv_file.close()
    gc.collect()  # Clear out variables from memory

    return data


def read_sis_csv(file_name: str) -> List[Dict[str, str]]:
    """
    Reads a CSV file and extracts the first name, last name, and email
        columns.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        list of dict: A list of dictionaries containing 'first_name',
            'last_name', and 'email'.
    """
    start_mem = memory_usage(PID)
    data: List[Dict[str, str]] = []
    recorded_emails = set()  # Will help avoid duplicate entries

    # Open file
    with open(file_name, mode="r", newline="", encoding="UTF-8") as csv_file:
        # Set reader
        csv_reader = csv.DictReader(csv_file)

        log.info("Parsing sis csv")

        # Wrap in tqdm if being ran interactively
        iterator = (
            tqdm(
                csv_reader, total=count_lines(file_name), desc="Read SIS File"
            )
            if IS_INTERACTIVE
            else csv_reader
        )

        if not hasattr(iterator, "__iter__"):
            raise ValueError("read_sis_csv iterator is not iterable.")

        # Extract useful columns
        for row in iterator:
            if (
                row["Email_Addr"] not in recorded_emails
                and row["Email_Addr"] != ""
            ):
                try:
                    data.append(
                        {
                            "School ID": row["SchoolID"],
                            "First Name": row["First_Name"],
                            "Last Name": row["Last_Name"],
                            "Email": row["Email_Addr"],
                        }
                    )

                    recorded_emails.add(row["Email_Addr"])  # Track email

                except IndexError:
                    data.append(
                        {
                            "First Name": "",
                            "Last Name": "",
                            "Email": row["Email_Addr"],
                        }
                    )
                    log.error(
                        "%s: Either first name or last name was provided.",
                        str(row),
                    )
                    continue

    log.info("Data retrieved")
    log.debug(
        "Total memory used: %iKiB",
        calculate_memory(start_mem, memory_usage(PID)),
    )

    csv_file.close()
    gc.collect()  # Clear out variables from memory

    return data


def read_command_csv(file_name: str) -> List[Dict[str, str]]:
    """
    Reads a CSV file and extracts the first name, last name, card number
        and email columns.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        list of dict: A list of dictionaries containing 'first_name',
            'last_name', and 'email'.
    """
    start_mem = memory_usage(PID)
    data: List[Dict[str, str]] = []

    # Open file
    with open(file_name, mode="r", newline="", encoding="UTF-8") as csv_file:
        # Set reader
        csv_reader = csv.DictReader(csv_file)

        log.info("Parsing sis csv")

        # Wrap in tqdm if being ran interactively
        iterator = (
            tqdm(
                csv_reader,
                total=count_lines(file_name),
                desc="Read Command File",
            )
            if IS_INTERACTIVE
            else csv_reader
        )

        if not hasattr(iterator, "__iter__"):
            raise ValueError("read_command_csv iterator is not iterable.")

        # Extract useful columns
        for row in iterator:
            try:
                data.append(
                    {
                        "First Name": row["firstName"],
                        "Last Name": row["lastName"],
                        "Email": row["email"],
                        "Card Number": row["cardNumber"],
                    }
                )
            except IndexError:
                data.append(
                    {
                        "First Name": "",
                        "Last Name": "",
                        "Email": row["Email"],
                    }
                )
                log.error(
                    "%s: Either first name or last name was provided.",
                    str(row),
                )
                continue

    log.info("Data retrieved")
    log.debug(
        "Total memory used: %iKiB",
        calculate_memory(start_mem, memory_usage(PID)),
    )

    csv_file.close()
    gc.collect()  # Clear out variables from memory

    return data


def collect_groups(
    sis_users_list: List[Dict[str, str]],
    index: int,
    current_name: Optional[str] = None,
    collected_groups: Optional[List[str]] = None,
) -> List[str]:
    """
    Collect groups associated with a specific email from the SIS users
    list recursively.

    Args:
        sis_users_list (list): A list of dictionaries containing user
            information.
        index (int): The current index in the SIS users list.
        current_email (str, optional): The current email being processed.
            Defaults to None.
        collected_groups (list, optional): List of collected groups for
            the current email. Defaults to None.

    Returns:
        list: A list of groups associated with the specified email.
    """

    if collected_groups is None:
        collected_groups = []

    # Base case: End of the list
    if index >= len(sis_users_list):
        return collected_groups

    current_user = sis_users_list[index]
    full_name = f"{current_user['First Name']} {current_user['Last Name']}"

    # Initialize current_name on the first call
    if current_name is None:
        current_name = full_name

    # If we have moved to a different email, return the accumulated groups
    if full_name != current_name:
        return collected_groups

    # Process the current SchoolID
    school_id = current_user["School ID"]

    if school_id in SCHOOL_ID_MAPPING:
        group = SCHOOL_ID_MAPPING[school_id]

        if group not in collected_groups:
            collected_groups.append(group)

    # Recurse to the next item
    return collect_groups(
        sis_users_list, index + 1, current_name, collected_groups
    )


def process_sis_users(sis_users_list: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Process the SIS users list to collect user groups for each unique
        email.

    Args:
        sis_users_list (list): A list of dictionaries containing user
            information, including email.

    Returns:
        dict: A dictionary where keys are unique email addresses and
            values are comma-separated user groups.
    """

    # Initialize an empty dictionary for storing user groups
    user_groups = {}

    index = 0
    while index < len(sis_users_list):
        current_user = sis_users_list[index]

        if full_name := (
            f"{current_user['First Name']} " f"{current_user['Last Name']}"
        ):
            if full_name not in user_groups:

                # Collect groups for the current email
                groups = collect_groups(sis_users_list, index, full_name)
                user_groups[full_name] = ";".join(groups)

            # Skip ahead to the next unique email
            while (
                index < len(sis_users_list)
                and f"{sis_users_list[index]['First Name']} "
                f"{sis_users_list[index]['Last Name']}" == full_name
            ):
                index += 1

        else:
            index += 1

    return user_groups


def compile_data_for_csv(
    third_party_csv: str, sis_csv: str, current_csv: str
) -> List[Dict[str, str]]:
    """
    Will take two dictionaries and prepare the data to be written to a
        csv.

    Args:
        command_csv (list of dict): The imported data from the csv
            imported by Command.
        third_party_csv (list of dict): The imported data from the csv
            imported by the third-party Access Control provider.

    Returns:
        list of dict: Returns all matching values between the two csvs.
    """
    start_mem = memory_usage(PID)
    compiled_data = []

    log.info("Reading csv files")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_ac_users = executor.submit(read_ac_csv, third_party_csv)
        future_sis_users = executor.submit(read_sis_csv, sis_csv)
        future_current_users = executor.submit(read_command_csv, current_csv)

        ac_users_list = future_ac_users.result()
        sis_users_list = future_sis_users.result()
        current_users_list = future_current_users.result()
    log.info("CSV files read successfully")

    email_thread = threading.Thread(
        target=add_to_domain,
        args=(current_users_list,),
    )
    email_thread.start()

    # Creating a lookup dictionary
    current_users_lookup = {
        user["Email"]: user for user in current_users_list if user["Email"]
    }
    ac_users_lookup = {
        (user["First Name"].strip(), user["Last Name"].strip()): user
        for user in ac_users_list
    }

    # Process SIS users to collect groups
    user_groups = process_sis_users(sis_users_list)

    # NOTE: Uncomment for updated_users to have only groups added
    # update_users_thread = threading.Thread(
    #     target=update_current_users_with_groups,
    #     args=(
    #         CSV_CURRENT_USERS,
    #         user_groups,
    #     ),
    # )
    # update_users_thread.start()

    # NOTE: Uncomment for updated_users.csv to have groups and emails added
    groups_and_emails_thread = threading.Thread(
        target=update_current_users_with_groups_and_emails,
        args=(
            CSV_CURRENT_USERS,
            user_groups,
            current_users_list,
        ),
    )
    groups_and_emails_thread.start()

    for sis_user in sis_users_list:
        try:
            email = sis_user["Email"]
            if (
                email
                and email in current_users_lookup
                and not current_users_lookup[email]["Card Number"]
            ):
                first_name = sis_user["First Name"]
                last_name = sis_user["Last Name"]
                full_name = f"{first_name} {last_name}"

                log.debug("Checking names %s", first_name)

                if ac_user := ac_users_lookup.get((first_name, last_name)):
                    log.debug("Match! Adding to compiled data")
                    compiled_data.append(
                        {
                            "firstName": first_name,
                            "lastName": last_name,
                            "email": email,
                            "cardFormat": CARD_TYPE,
                            "facilityCode": "103",
                            "cardNumber": ac_user["Card Number"],
                            "groups": user_groups.get(full_name, ""),
                        }
                    )

                else:
                    log.debug("No matching case for %s", email)

        except KeyError as e:
            log.warning("A field was found empty in %s", sis_user)
            log.error(e)
            continue

    log.info("Finished compiling csv files.")
    log.debug(
        "Total memory used: %iKiB",
        calculate_memory(start_mem, memory_usage(PID)),
    )

    groups_and_emails_thread.join()
    email_thread.join()
    # update_users_thread.join()
    gc.collect()  # Clear out variables from memory

    return compiled_data


def validate_and_update_email(
    user: Dict[str, str], email_pattern: re.Pattern
) -> Dict[str, str]:
    """
    Validate and update the email format of a user.

    Args:
        user (Dict[str, str]): A dictionary containing user information
        with keys 'firstName', 'lastName', and 'Email'.
        email_pattern (re.Pattern): Compiled regex pattern to match
        against the email.

    Returns:
        Dict[str, str]: A dictionary with the user's full name and
        updated email if necessary.
    """
    email = user.get("Email", "")
    if not email_pattern.match(email):
        # Convert to lowercase for consistency
        first_name = user.get("First Name", "").lower()
        last_name = user.get("Last Name", "").lower()
        new_email = f"{first_name}.{last_name}{DOMAIN}"
        return {"Name": f"{first_name} {last_name}", "Email": new_email}
    return {}


def update_current_users_with_groups_and_emails(
    file_name: str,
    processed_sis_users: Dict[str, str],
    user_list: List[Dict[str, str]],
) -> None:
    """
    Updates current users with groups and emails based on processed SIS users.

    Args:
        file_name: The name of the CSV file to update.
        processed_sis_users: A dictionary mapping user full names to email
            addresses.
        user_list: A list of dictionaries containing user information.

    Raises:
        ValueError: If the csv_iterator is not iterable.
    """
    start_mem = memory_usage(PID)
    domain_pattern = re.escape(DOMAIN)
    email_pattern = re.compile(rf"^[a-z]+(\.[a-z]+)?\.[a-z]+{domain_pattern}$")
    need_an_email: List[Dict[str, str]] = []

    def process_user(user: Dict[str, str]) -> None:
        """Validate and update user's email."""
        updated_info = validate_and_update_email(user, email_pattern)
        if updated_info:
            need_an_email.append(updated_info)
            user["Email"] = updated_info["Email"]

    def update_groups(user: Dict[str, str], full_name: str) -> None:
        """Update user's groups based on processed SIS users."""
        if full_name in processed_sis_users:
            existing_groups = user.get("groups", "").strip()
            new_groups = processed_sis_users[full_name]
            user["groups"] = (
                f"{existing_groups}; {new_groups}"
                if existing_groups
                else new_groups
            )

    # Typing the iterator as Union ensures compatibility
    iterator: Union[List[Dict[str, str]], tqdm] = user_list

    # Use tqdm if running interactively
    iterator = (
        tqdm(user_list, desc="Adding Groups & Emails")
        if IS_INTERACTIVE
        else user_list
    )

    if not hasattr(iterator, "__iter__"):
        raise ValueError(
            "update_current_users_with_groups_and_emails iterator is not "
            "iterable."
        )

    # Process user list to ensure emails are correctly formatted
    for user in iterator:
        process_user(user)

    with (
        open(file_name, "r", newline="", encoding="UTF-8") as current_file,
        open(
            "updated_users.csv", "w", newline="", encoding="UTF-8"
        ) as group_file,
    ):

        csv_reader = csv.DictReader(current_file)
        group_writer = csv.DictWriter(
            group_file, fieldnames=csv_reader.fieldnames or []
        )
        group_writer.writeheader()

        total_count = count_lines(
            file_name
        )  # Ensure count_lines is defined correctly
        csv_iterator = (
            tqdm(csv_reader, total=total_count, desc="Writing Groups & Emails")
            if IS_INTERACTIVE
            else csv_reader
        )

        if not hasattr(csv_iterator, "__iter__"):
            raise ValueError(
                "update_current_users_with_groups_and_emails csv_iterator is "
                "not iterable."
            )

        for user in csv_iterator:
            full_name = f"{user['firstName']} {user['lastName']}"
            update_groups(user, full_name)
            group_writer.writerow(user)

    log.info(
        "Data updated and written to updated_users.csv and "
        "need_email_domain.csv"
    )
    log.debug(
        "Total memory used: %iKiB",
        calculate_memory(start_mem, memory_usage(PID)),
    )

    gc.collect()  # Clear out variables from memory


def update_current_users_with_groups(
    file_name: str, processed_sis_users: Dict[str, str]
):
    """
    Updates current users with groups in a CSV file by calling the
    extract_current_users_with_groups function.

    Args:
        file_name: The name of the CSV file to update.
        processed_sis_users: A dictionary mapping user full names to lists of
            groups.

    Returns:
        None
    """
    start_mem = memory_usage(PID)

    # Open the original file and a new file for the updated data
    with (
        open(file_name, "r", newline="", encoding="UTF-8") as current_file,
        open(
            "updated_users.csv", "w", newline="", encoding="UTF-8"
        ) as group_file,
    ):
        extract_current_users_with_groups(
            current_file, group_file, file_name, processed_sis_users
        )
    log.info("Data updated and written to updated_users.csv")
    log.debug(
        "Total memory used: %iKiB",
        calculate_memory(start_mem, memory_usage(PID)),
    )

    group_file.close()
    current_file.close()
    gc.collect()  # Clear out variables from memory


def extract_current_users_with_groups(
    current_file: TextIO,
    group_file: TextIO,
    file_name: str,
    processed_sis_users: Dict[str, str],
):
    """
    Extracts current users with groups from a CSV file and updates the
    groups for each user based on processed SIS users.

    Args:
        current_file: The CSV file containing the current users.
        group_file: The CSV file to write the updated users with groups.
        file_name: The name of the CSV file being processed.
        processed_sis_users: A dictionary mapping user full names to
            lists of groups.

    Returns:
        None

    Raises:
        ValueError: If the iterator is not iterable.

    Examples:
        extract_current_users_with_groups(
            current_file,
            group_file,
            "users.csv",
            processed_sis_users
        )
    """
    csv_reader = csv.DictReader(current_file)
    group_fieldnames = csv_reader.fieldnames or []
    group_writer = csv.DictWriter(group_file, fieldnames=group_fieldnames)

    group_writer.writeheader()

    # Check if the environment is interactive
    iterator = (
        tqdm(
            csv_reader,
            total=count_lines(file_name),
            desc="Extracting and Writing Groups",
        )
        if IS_INTERACTIVE
        else csv_reader
    )

    if not hasattr(iterator, "__iter__"):
        raise ValueError(
            "extract_current_users_with_groups iterator is not iterable."
        )

    # Process each row in the original file
    for user in iterator:
        full_name = f"{user['firstName']} {user['lastName']}"
        if full_name in processed_sis_users:
            existing_groups = user.get("groups", "").strip()
            new_groups = "".join(processed_sis_users[full_name])
            if existing_groups and new_groups:
                user["groups"] = f"{existing_groups}; {new_groups}"
            elif existing_groups:
                user["groups"] = existing_groups
            else:
                user["groups"] = new_groups
        # Write the updated user to the new file
        group_writer.writerow(user)


def add_to_domain(user_list: List[Dict[str, str]]):
    """
    Adds users to a domain by validating and updating their email addresses
    based on a specified domain pattern.

    Args:
        user_list: A list of dictionaries containing user information.

    Returns:
        None

    Raises:
        ValueError: If the iterator is not iterable.
    """
    start_mem = memory_usage(PID)

    # Regex pattern for email in the format first_name.last_name@juabsd.org
    domain_pattern = re.escape(DOMAIN)
    email_pattern = re.compile(rf"^[a-z]+(\.[a-z]+)?\.[a-z]+{domain_pattern}$")

    need_an_email = []

    # Wrap in tqdm if being ran interactively
    iterator = (
        tqdm(user_list, desc="Adding Email Domains")
        if IS_INTERACTIVE
        else user_list
    )

    if not hasattr(iterator, "__iter__"):
        raise ValueError("add_to_domain iterator is not iterable.")

    for user in iterator:
        if updated_info := validate_and_update_email(user, email_pattern):
            need_an_email.append(updated_info)

    # Write the need_an_email list to the CSV file
    with open(
        "need_email_domain.csv", "w", newline="", encoding="UTF-8"
    ) as email_file:
        check_needed_email(email_file, need_an_email)
    log.info("Data updated and written to need_email_domain.csv")
    log.debug(
        "Total memory used: %iKiB",
        calculate_memory(start_mem, memory_usage(PID)),
    )

    email_file.close()
    gc.collect()


def check_needed_email(email_file, need_an_email):
    """
    Checks and writes needed email data to a CSV file.

    Args:
        email_file: The CSV file to write the email data to.
        need_an_email: An iterable containing the needed email data.

    Returns:
        None

    Raises:
        ValueError: If the iterator is not iterable.
    """
    email_fieldnames = ("Name", "Email")
    csv_writer = csv.DictWriter(email_file, fieldnames=email_fieldnames)
    csv_writer.writeheader()

    # Wrap in tqdm if being ran interactively
    email_iterator = (
        tqdm(need_an_email, desc="Writing Needed Emails")
        if IS_INTERACTIVE
        else need_an_email
    )

    if not hasattr(email_iterator, "__iter__"):
        raise ValueError("check_needed_email iterator is not iterable.")

    for email_data in email_iterator:
        csv_writer.writerow(email_data)


if ac_user_list := compile_data_for_csv(
    CSV_AC_LIST, CSV_SIS_USERS, CSV_CURRENT_USERS
):
    log.info("Writing file")
    with open(CSV_OUTPUT, "w", newline="", encoding="UTF-8") as file:
        fieldnames = (
            "firstName",
            "lastName",
            "middleName",
            "email",
            "userId",
            "externalId",
            "companyName",
            "employeeId",
            "employeeType",
            "employeeTitle",
            "department",
            "departmentId",
            "startDate",
            "endDate",
            "roles",
            "cardFormat",
            "facilityCode",
            "cardNumber",
            "cardNumberHex",
            "licensePlateNumbers",
            "entryCode",
            "groups",
            "cloudUnlock",
            "bluetoothUnlock",
            "photoUrl",
        )
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        # Wrap in tqdm if being ran interactively
        missing_users_iterator = (
            tqdm(ac_user_list, desc="Writing Missing Users")
            if IS_INTERACTIVE
            else ac_user_list
        )

        if not hasattr(missing_users_iterator, "__iter__"):
            raise ValueError("Missing Users iterator is not iterable.")

        for final_row in missing_users_iterator:
            writer.writerow(final_row)
    log.info("Written to file")
