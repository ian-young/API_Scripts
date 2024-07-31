"""
Author: Ian Young
Purpose: This script will compare three csvs and generate a fourth with
    access users that are in the old system and sis but not in Command.
"""

import concurrent.futures
import csv
import gc
import logging
from os import getpid
from typing import Dict, List

from tqdm import tqdm

from QoL.verbose_compute import memory_usage

PID = getpid()

CSV_OUTPUT = "formatted_users.csv"
CSV_AC_LIST = "LegacySystemExport.csv"
CSV_SIS_USERS = "SISExport.csv"
CSV_CURRENT_USERS = "VerkadaExport.csv"
CARD_TYPE = "Standard 26-bit Wiegand"
STATUS = "Active"

SCHOOL_ID_MAPPING = {
    "704": "(JHS)",
    "304": "(JJHS)",
    "114": "(ES)",
    "110": "(ESS)",
    "112": "(ESSS)"
}

calculate_memory = lambda start_mem, end_mem: end_mem - start_mem

log = logging.getLogger()
LOG_LEVEL = logging.WARNING
logging.basicConfig(
    level=LOG_LEVEL, format="(%(asctime)s) %(levelname)s: %(message)s"
)
log.setLevel(LOG_LEVEL)


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
        for row in tqdm(csv_reader, desc="Read legacy file"):
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
        for row in tqdm(csv_reader, desc="Read sis csv"):
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
        for row in tqdm(csv_reader, desc="Read Command csv"):
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

    gc.collect()  # Clear out variables from memory

    return data


def collect_groups(sis_users_list, index, current_email=None, collected_groups=None):
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
    email = current_user["Email"]

    # Initialize current_email on the first call
    if current_email is None:
        current_email = email

    # If we have moved to a different email, return the accumulated groups
    if email != current_email:
        return collected_groups

    # Process the current SchoolID
    school_id = current_user["School ID"]

    if school_id in SCHOOL_ID_MAPPING:
        group = SCHOOL_ID_MAPPING[school_id]

        if group not in collected_groups:
            collected_groups.append(group)

    # Recurse to the next item
    return collect_groups(sis_users_list, index + 1, current_email, collected_groups)


def process_sis_users(sis_users_list: List[Dict[str, str]]) -> Dict[str,str]:
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

        if email := current_user["Email"]:
            if email not in user_groups:

                # Collect groups for the current email
                groups = collect_groups(sis_users_list, index, email)
                user_groups[email] = ";".join(groups)

            # Skip ahead to the next unique email
            while index < len(sis_users_list) and sis_users_list[index]["Email"] == email:
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
                            "groups": user_groups.get(email, "")
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

    gc.collect()  # Clear out variables from memory

    return compiled_data


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
            "photoUrl"
        )
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for final_row in tqdm(ac_user_list, desc="Writing Missing Users"):
            writer.writerow(final_row)
    log.info("Written to file")
