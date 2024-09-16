"""
Author: Ian Young
Purpose: Graph how many public Verkada API endpoints return with a 200 and
track how many 429s we receive to track endpoint load, too.
"""

# Import essential libraries
import datetime
import re

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from tools import log

# Update with your log file path
LOG_FILE_PATH = "/Users/ian.young/Documents/.scripts/Python/API_Scripts/\
endpoint_data.log"


def parse_log_file(log_file_path):
    """
    Imports and parses a file to extract the data from endpoint test entries.

    :param log_file_path: The path to the log file that contains the entries.
    :type log_file_path: str
    :return: Returns the formatted and parsed data from the log file.
    :rtype: list
    """
    try:
        with open(log_file_path, "r", encoding="utf-8") as log_file:
            lines = log_file.readlines()

            data = {"time": [], "failed": [], "retries": []}
            current_time = None

            for line in lines:
                time_match = re.match(
                    r"Time of execution: (\d+/\d+ \d+:\d+:\d+)", line
                )
                failed_match = re.match(r"Failed endpoints: (\d+)", line)
                retries_match = re.match(r"Retries: (\d+)", line)

                if time_match:
                    current_year = (
                        datetime.datetime.now().year
                    )  # Get the current year
                    current_time = datetime.datetime.strptime(
                        f"{current_year}/{time_match[1]}",
                        "%Y/%m/%d %H:%M:%S",
                    )
                    log.info("Found time: %s", str(current_time))

                elif failed_match and current_time:
                    data["time"].append(current_time)
                    data["failed"].append(int(failed_match[1]))
                    log.info("Found failed: %d", int(failed_match[1]))

                elif retries_match and current_time:
                    data["retries"].append(int(retries_match[1]))
                    current_time = None
                    log.info("Found retries: %d", int(retries_match[1]))

        log.info("Parsed data: %s", str(data))

        return data

    except Exception as e:
        log.error(
            "An error has occurred while extracting the data. Error: %s",
            str(e),
        )
        raise e


def create_bar_graph(data):
    """
    Creates a bar graph given a data set.

    :param data: The data set to work with.
    :type data: list
    """
    # Set the background color to dark gray
    _, ax = plt.subplots(figsize=(10, 6), facecolor="black")

    # Adjust the width and spacing of each bar
    bar_width, bar_spacing = 0.5, 0.1

    # Set chart background
    ax.set_facecolor("#1F1F1F")

    # Bar graph for failed endpoints
    ax.bar(
        range(len(data["time"])),
        data["failed"],
        width=bar_width,
        color="red",
        label="Failed Endpoints",
        align="center",
        edgecolor="#1F1F1F",
    )

    # Bar graph for retries
    retries_x = [i + bar_width + bar_spacing for i in range(len(data["time"]))]
    ax.bar(
        retries_x,
        data["retries"],
        width=bar_width,
        color="yellow",
        label="Retries",
        align="center",
        edgecolor="#1F1F1F",
    )

    # Set x-axis ticks and labels
    num_ticks = len(data["time"])
    x_ticks = [i + bar_width / 2 + bar_spacing for i in range(num_ticks)]

    # Calculate the dynamic interval based on the number of data points
    # You can adjust the divisor to control the number of ticks
    interval = max(1, num_ticks // 8)

    ax.set_xticks(x_ticks[::interval])
    ax.set_xticklabels(
        [time.strftime("%H:%M") for time in data["time"]][::interval],
        rotation=45,
        ha="right",
        color="white",
    )

    # Set y-axis scale based on the maximum count in both
    # 'failed' and 'retries'
    max_fail = max(data["failed"])
    max_retries = max(data["retries"])
    max_y = max(max_fail, max_retries)
    ax.set_yticks(range(max_y + 1))
    ax.set_yticklabels(range(max_y + 1), color="white")

    # Set axis label color to white
    ax.set_xlabel("Time of Execution", color="white")
    ax.set_ylabel("Count", color="white")  # Set axis label color to white
    ax.set_title(
        "Failed Endpoints and Retries Over Time", color="white"
    )  # Set title color to white

    # Set x-axis tick label color to white
    ax.tick_params(axis="x", colors="white")
    # Set y-axis tick label color to white
    ax.tick_params(axis="y", colors="white")

    # Add grid lines to the y-axis
    ax.yaxis.grid(color="gray", linestyle=":", linewidth=0.5)

    ax.legend()

    plt.tight_layout()
    plt.show()


def create_line_graph(data):
    """
    Creates a line graph given a data set.

    :param data: The data set to work with.
    :type data: list
    """
    # Set the background color to dark gray
    # Dark gray background
    _, ax = plt.subplots(figsize=(10, 6), facecolor="black")

    # Set the chart background color to dark gray
    ax.set_facecolor("#1F1F1F")

    # Plotting line for retries without markers
    ax.plot(
        data["time"],
        data["retries"],
        label="Retries",
        color="yellow",
        marker=".",
    )

    # Plotting line for failed endpoints without markers
    ax.plot(
        data["time"],
        data["failed"],
        label="Failed Endpoints",
        color="red",
        linewidth=2.5,
        marker=".",
    )

    # Set axis label color to white
    ax.set_xlabel("Time of Execution", color="white")
    ax.set_ylabel("Count", color="white")  # Set axis label color to white
    ax.set_title(
        "Failed Endpoints and Retries Over Time", color="white"
    )  # Set title color to white

    # Set x-axis tick label color to white
    ax.tick_params(axis="x", colors="white")
    # Set y-axis tick label color to white
    ax.tick_params(axis="y", colors="white")

    # Add grid lines to the y-axis
    ax.yaxis.grid(color="gray", linestyle=":", linewidth=0.5)

    # Customize x-axis ticks for better readability
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    ax.legend()

    plt.tight_layout()
    plt.show()


# Run if being ran directly and not imported
if __name__ == "__main__":
    log_data = parse_log_file(LOG_FILE_PATH)
    log.debug(log_data)  # Print the parsed data for debugging
    create_line_graph(log_data)
