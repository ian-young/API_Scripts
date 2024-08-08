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
from os import getpid
from typing import Dict, List, Optional

from tqdm import tqdm

from QoL.verbose_compute import memory_usage

PID = getpid()

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
LOG_LEVEL = logging.DEBUG
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
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
        for row in tqdm(
            csv_reader, total=count_lines(file_name), desc="Read legacy file"
        ):
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
        # Extract useful columns
        for row in tqdm(
            csv_reader, total=count_lines(file_name), desc="Read sis csv"
        ):
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
        # Extract useful columns
        for row in tqdm(
            csv_reader, total=count_lines(file_name), desc="Read Command csv"
        ):

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

        if (
            full_name := f"{current_user['First Name']} {current_user['Last Name']}"
        ):
            if full_name not in user_groups:

                # Collect groups for the current email
                groups = collect_groups(sis_users_list, index, full_name)
                user_groups[full_name] = ";".join(groups)

            # Skip ahead to the next unique email
            while (
                index < len(sis_users_list)
                and f"{sis_users_list[index]['First Name']} {sis_users_list[index]['Last Name']}"
                == full_name
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
    # update_users_thread = threading.Thread(
    #     target=update_current_users_with_groups,
    #     args=(
    #         CSV_CURRENT_USERS,
    #         user_groups,
    #     ),
    # )
    # update_users_thread.start()
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
        first_name = user.get("First Name", "").lower()
        last_name = user.get("Last Name", "").lower()
        new_email = f"{first_name}.{last_name}{DOMAIN}"
        return {"Name": f"{first_name} {last_name}", "Email": new_email}
    return {}


def update_current_users_with_groups_and_emails(
    file_name: str,
    processed_sis_users: Dict[str, str],
    user_list: List[Dict[str, str]],
):
    """
    Update the current users with their respective groups based on
    processed SIS users and ensure that their email addresses are in the
    correct format.

    Args:
        file_name (str): The name of the original file to read user data
        from.
        processed_sis_users (Dict[str, str]): A dictionary mapping full
        names to their associated groups.
        user_list (List[Dict[str, str]]): A list of dictionaries
        containing user information with keys 'Email', 'firstName', and
        'lastName'.

    Returns:
        None

    Raises:
        This function does not raise any exceptions.

    Examples:
        update_current_users_with_groups_and_emails("users.csv", {
            "John Doe": "Group1; Group2"
        }, user_list)
    """
    start_mem = memory_usage(PID)

    # Regex pattern for email in the format first_name.last_name@juabsd.org
    domain_pattern = re.escape(DOMAIN)
    email_pattern = re.compile(rf"^[a-z]+(\.[a-z]+)?\.[a-z]+{domain_pattern}$")

    need_an_email = []

    # Process the user_list to ensure emails are correctly formatted
    for user in tqdm(user_list, desc="Adding updated info"):
        if updated_info := validate_and_update_email(user, email_pattern):
            need_an_email.append(updated_info)
            user["Email"] = updated_info["Email"]

    # Open the original file and a new file for the updated data
    with (
        open(file_name, "r", newline="", encoding="UTF-8") as current_file,
        open(
            "updated_users.csv", "w", newline="", encoding="UTF-8"
        ) as group_file,
    ):

        csv_reader = csv.DictReader(current_file)
        group_fieldnames = csv_reader.fieldnames or []
        group_writer = csv.DictWriter(group_file, fieldnames=group_fieldnames)

        group_writer.writeheader()

        # Process each row in the original file
        for user in tqdm(
            csv_reader,
            total=count_lines(file_name),
            desc="Writing Updated Users",
        ):
            full_name = f"{user['firstName']} {user['lastName']}"

            if updated_info := validate_and_update_email(user, email_pattern):
                user["email"] = updated_info["Email"]

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

    log.info(
        "Data updated and written to updated_users.csv and need_email_domain.csv"
    )
    log.debug(
        "Total memory used: %iKiB",
        calculate_memory(start_mem, memory_usage(PID)),
    )

    current_file.close()
    group_file.close()
    gc.collect()  # Clear out variables from memory


def update_current_users_with_groups(
    file_name: str, processed_sis_users: Dict[str, str]
):
    """
    Update the current users with their respective groups based on
        processed SIS users.

    Args:
        file_name (str): The name of the original file to read user data
            from.
        processed_sis_users (Dict[str, str]): A dictionary mapping user
            emails to their associated groups.

    Returns:
        None

    Raises:
        This function does not raise any exceptions.

    Examples:
        update_current_users_with_groups("users.csv", {
            "user1@example.com": ["Group1", "Group2"]
        })
    """
    start_mem = memory_usage(PID)

    # Open the original file and a new file for the updated data
    with (
        open(file_name, "r", newline="", encoding="UTF-8") as current_file,
        open(
            "updated_users.csv", "w", newline="", encoding="UTF-8"
        ) as group_file,
    ):
        csv_reader = csv.DictReader(current_file)
        group_fieldnames = csv_reader.fieldnames or []
        group_writer = csv.DictWriter(group_file, fieldnames=group_fieldnames)

        group_writer.writeheader()

        # Process each row in the original file
        for user in tqdm(
            csv_reader,
            total=count_lines(file_name),
            desc="Writing Updated Users",
        ):
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

    log.info("Data updated and written to updated_users.csv")
    log.debug(
        "Total memory used: %iKiB",
        calculate_memory(start_mem, memory_usage(PID)),
    )

    group_file.close()
    current_file.close()
    gc.collect()  # Clear out variables from memory


def add_to_domain(user_list: List[Dict[str, str]]):
    """
    Add domain to email addresses in a list of users if they do not
    already have it.

    Args:
        user_list (List[Dict[str, str]]): A list of dictionaries
        containing user information with keys 'email', 'firstName', and
        'lastName'.

    Returns:
        None

    Raises:
        None
    """
    start_mem = memory_usage(PID)

    # Regex pattern for email in the format first_name.last_name@juabsd.org
    domain_pattern = re.escape(DOMAIN)
    email_pattern = re.compile(rf"^[a-z]+(\.[a-z]+)?\.[a-z]+{domain_pattern}$")

    need_an_email = []

    for user in tqdm(user_list, desc="Adding emails"):
        if updated_info := validate_and_update_email(user, email_pattern):
            need_an_email.append(updated_info)

    # Write the need_an_email list to the CSV file
    with open(
        "need_email_domain.csv", "w", newline="", encoding="UTF-8"
    ) as email_file:
        email_fieldnames = ("Name", "Email")
        csv_writer = csv.DictWriter(email_file, fieldnames=email_fieldnames)
        csv_writer.writeheader()
        for email_data in tqdm(need_an_email, desc="Writing emails"):
            csv_writer.writerow(email_data)

    log.info("Data updated and written to need_email_domain.csv")
    log.debug(
        "Total memory used: %iKiB",
        calculate_memory(start_mem, memory_usage(PID)),
    )

    email_file.close()
    gc.collect()


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
        for final_row in tqdm(ac_user_list, desc="Writing Missing Users"):
            writer.writerow(final_row)
    log.info("Written to file")
