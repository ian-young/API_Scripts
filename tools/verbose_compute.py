"""
Author: Ian Young
Purpose: This is a module that may be imported for improved verbosity on
    compute resources.
"""

from gc import collect
from typing import Optional

import psutil

from .log import log


def memory_usage(process_id: int) -> float:
    """
    Calculate the memory usage of the current process.

    Args:
        process_id (int): The process ID for which memory usage needs to be
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


def calculate_memory(start_mem: float, end_mem: float) -> float:
    """Calculate the difference in memory usage.

    This function computes the amount of memory used by subtracting the
    starting memory value from the ending memory value.

    Args:
        start_mem (float): The initial memory usage.
        end_mem (float): The final memory usage.

    Returns:
        float: The difference in memory usage.
    """

    return end_mem - start_mem
