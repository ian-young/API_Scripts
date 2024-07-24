"""
Author: Ian Young
Purpose: This script will compare two csvs and generate a third with
access users that should be in Command.
"""

import csv
import logging
import gc
from os import getpid
from typing import List, Dict

from QoL.verbose_compute import memory_usage, cpu_usage

PID = getpid()

CSV_OUTPUT = (
    "/Users/ian.young/Documents/.scripts/API_Scripts/"
    "Customer_Projects/formatted_users.csv"
)
CSV_AC_LIST = (
    "/Users/ian.young/Documents/.scripts/API_Scripts/"
    "Customer_Projects/test_csv_1.csv"
)
CSV_SIS_USERS = (
    "/Users/ian.young/Documents/.scripts/API_Scripts/"
    "Customer_Projects/test_csv_2.csv"
)
CARD_TYPE = "Standard 26-bit Wiegand"
STATUS = "Active"

calculate_memory = lambda start_mem, end_mem: end_mem - start_mem

log = logging.getLogger()
LOG_LEVEL = logging.DEBUG
logging.basicConfig(
    level=LOG_LEVEL,
    format="(%(asctime)s.%(msecs)03d) %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log.setLevel(LOG_LEVEL)


def read_ac_csv(file_name: str) -> List[Dict[str, str]]:
    """
    Reads a CSV file and extracts the first name, last name, and email columns.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        list of dict: A list of dictionaries containing 'first_name', 'last_name', and 'email'.
    """
    start_mem = memory_usage(PID)
    data: List[Dict[str, str]] = []

    # Open file
    with open(file_name, mode="r", newline="", encoding="UTF-8") as csv_file:
        # Set reader
        csv_reader = csv.DictReader(csv_file)

        log.debug("Parsing access control csv")
        # Extract useful columns
        data.extend(
            {
                "Email": row["Email"],
                "Facility Code": row["Facility Code"],
                "Card Number": row["Card Number"],
                "Entry Code": row["Entry Code"],
            }
            for row in csv_reader
        )
    log.debug("Data retrieved")
    log.debug(
        "Total memory used: %iKiB", calculate_memory(start_mem, memory_usage(PID))
    )

    gc.collect()  # Clear out variables from memory

    return data


def read_sis_csv(file_name: str) -> List[Dict[str, str]]:
    """
    Reads a CSV file and extracts the first name, last name, and email columns.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        list of dict: A list of dictionaries containing 'first_name', 'last_name', and 'email'.
    """
    start_mem = memory_usage(PID)
    data: List[Dict[str, str]] = []

    # Open file
    with open(file_name, mode="r", newline="", encoding="UTF-8") as csv_file:
        # Set reader
        csv_reader = csv.DictReader(csv_file)

        log.debug("Parsing sis csv")
        # Extract useful columns
        for row in csv_reader:
            try:
                name_parts = row["Name"].split()
                data.append(
                    {
                        "First Name": name_parts[0],
                        "Last Name": name_parts[-1],
                        "Email": row["Email"],
                        "External ID": row["Employee ID"],
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

    log.debug("Data retrieved")
    log.debug(
        "Total memory used: %iKiB", calculate_memory(start_mem, memory_usage(PID))
    )

    gc.collect()  # Clear out variables from memory

    return data


def compile_data_for_csv(
    third_party_csv: str, sis_csv: str
) -> List[Dict[str, str]]:
    """
    Will take two dictionaries and prepare the data to be written to a csv.

    Args:
        command_csv (list of dict): The imported data from the csv
            imported by Command.
        third_party_csv (list of dict): The imported data from the csv
            imported by the third-party Access Control provider.

    Returns:
        list of dict: Returns all matching values between the two csvs.
    """
    start_cpu = cpu_usage(PID, None)
    start_mem = memory_usage(PID)
    compiled_data = []

    log.info("Reading csv files")
    ac_users_list = read_ac_csv(third_party_csv)
    sis_users_list = read_sis_csv(sis_csv)
    log.info("CSV files read successfully")

    # Creating a lookup dictionary
    existing_ac_user_emails = {user["Email"]: user for user in ac_users_list}

    for user in sis_users_list:
        log.debug("Running for: %s", str(user))
        try:
            if email := user["Email"]:
                log.debug("Testing for %s", user["Email"])
                if email in existing_ac_user_emails:
                    compiled_data.append(
                        {
                            "Email": email,
                            "External ID": user["External ID"],
                            "Card Type": CARD_TYPE,
                            "Facility Code": existing_ac_user_emails[email][
                                "Facility Code"
                            ],
                            "Card Number": existing_ac_user_emails[email][
                                "Card Number"
                            ],
                            "Card Number Hex": "",
                            "License Plate": "",
                            "Entry Code": existing_ac_user_emails[email][
                                "Entry Code"
                            ],
                            "Credential Status": STATUS,
                        }
                    )
                else:
                    log.debug("No matching case for %s", email)

        except KeyError as e:
            log.warning("A field was found empty in %s", user)
            log.error(e)
            continue

    log.info("Finished compiling csv files.")
    log.debug(
        "Total memory used: %iKiB", calculate_memory(start_mem, memory_usage(PID))
    )
    log.debug("CPU utilization: %.1f%%", cpu_usage(PID, None) - start_cpu)

    gc.collect()  # Clear out variables from memory

    return compiled_data


if ac_user_list := compile_data_for_csv(CSV_AC_LIST, CSV_SIS_USERS):
    with open(CSV_OUTPUT, "w", newline="", encoding="UTF-8") as file:
        fieldnames = (
            "Email",
            "User ID",
            "External ID",
            "Card Type",
            "Facility Code",
            "Card Number",
            "Card Number Hex",
            "License Plate",
            "Entry Code",
            "Credential Status",
        )
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ac_user_list)
