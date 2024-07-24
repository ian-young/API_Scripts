"""
Author: GPT4.o
Co-Author: Ian Young
Purpose: Test the cpu_usage script's ability to print CPU utilization
"""
import time
import multiprocessing

from QoL.verbose_compute import cpu_usage
def cpu_intensive_task(duration: int):
    """
    Simulate a CPU-intensive task that runs for a specified duration.

    Args:
        duration (int): The duration in seconds for which the task should run.
    """
    end_time = time.time() + duration
    while time.time() < end_time:
        pass


def cpu_usage_test():
    """
    Test the CPU usage of a CPU-intensive task running in a separate process.

    Returns:
        list: A list of CPU usage percentages of the process at different intervals.
    """

    # Start a CPU-intensive task in a separate process
    process = multiprocessing.Process(target=cpu_intensive_task, args=(10,))
    process.start()

    # Monitor CPU usage of the process

    usage_results = []
    for _ in range(5):
        usage = cpu_usage(process.pid)
        usage_results.append(usage)
        time.sleep(1)

    # Ensure the process finishes
    process.join()

    return usage_results


if __name__ == "__main__":
    print(cpu_usage_test())
