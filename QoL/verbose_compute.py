"""
Author: Ian Young
Purpose: This is a module that may be imported for improved verbosity on
    compute resources.
"""

import logging
from gc import collect
from typing import Optional

import psutil

log = logging.getLogger()
LOG_LEVEL = logging.DEBUG
log.setLevel(LOG_LEVEL)
logging.basicConfig(
    level=LOG_LEVEL,
    format=("(%(asctime)s.%(msecs)03d) %(levelname)s: %(message)s"),
    datefmt="%H:%M:%S"
)


def memory_usage(process_id: int) -> float:
    """
    Calculate the memory usage of the current process.

    Args:
        process_id (int): The process ID for which CPU usage needs to be
            calculated.

    Returns:
        float: The memory usage of the current process in kibibytes.
    """
    log.debug("Getting process memory")

    collect()  # Clear out variables from memory

    # Convert to kibibytes
    return psutil.Process(process_id).memory_info().rss / 1024


def cpu_usage(process_id: int, interval: Optional[int] = 1) -> float:
    """
    Calculate the CPU usage of a specified process.

    Args:
        process_id (int): The process ID for which CPU usage needs to be
            calculated.
        interval (Optional[int]): The time interval in seconds over which
            CPU usage is calculated. Defaults to 1.

    Returns:
        float: The CPU usage percentage of the specified process.
    """
    log.debug("Getting process CPU usage")

    return psutil.Process(process_id).cpu_percent(interval=interval)
