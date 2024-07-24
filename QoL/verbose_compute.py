"""
Author: Ian Young
Purpose: This is a module that may be imported for improved verbosity on
    compute resources.
"""

import logging
from gc import collect

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

    Returns:
        float: The memory usage of the current process in kibibytes.
    """
    log.debug("Getting process memory")
    process = psutil.Process(process_id)
    mem_info = process.memory_info()

    collect()  # Clear out variables from memory

    return mem_info.rss / 1024  # Convert to kibibytes


def cpu_usage(process_id: int) -> float:
    """
    Calculate the CPU usage of the current process.

    Returns:
        float: The CPU usage percentage of the current process.
    """
    log.debug("Getting process CPU usage")
    process = psutil.Process(process_id)

    return process.cpu_percent(interval=1)
