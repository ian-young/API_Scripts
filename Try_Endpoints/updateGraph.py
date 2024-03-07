import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re
import logging
import datetime
from endpointTests import log_file_path as log_file
from endpointTests import working_directory as directory

# Set logger
log = logging.getLogger()
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s"
)

logging.getLogger("matplotlib").setLevel(logging.CRITICAL)

# Update with your log file path
log_file_path = log_file
image_path = f"{directory}/endpoint_graph.png"


def parse_log_file(log_file_path):
    """
    Imports and parses a file to extract the data from endpoint test entries.

    :param log_file_path: The path to the log file that contains the entries.
    :type log_file_path: str
    :return: Returns the formatted and parsed data from the log file.
    :rtype: list
    """
    try:
        with open(log_file_path, 'r') as log_file:
            lines = log_file.readlines()

            data = {'time': [], 'failed': [], 'retries': []}
            current_time = None

            for line in lines:
                time_match = re.match(
                    r"Time of execution: (\d+/\d+ \d+:\d+:\d+)", line)
                failed_match = re.match(r"Failed endpoints: (\d+)", line)
                retries_match = re.match(r"Retries: (\d+)", line)

                if time_match:
                    if time_match:
                        current_year = datetime.datetime.now().year  # Get the current year
                        current_time = datetime.datetime.strptime(
                            f"{current_year}/{time_match.group(1)}",
                            '%Y/%m/%d %H:%M:%S')
                        log.info(f"Found time: {current_time}")

                elif failed_match and current_time:
                    data['time'].append(current_time)
                    data['failed'].append(int(failed_match.group(1)))
                    log.info(f"Found failed: {int(failed_match.group(1))}")
                elif retries_match and current_time:
                    data['retries'].append(int(retries_match.group(1)))
                    current_time = None
                    log.info(f"Found retries: {int(retries_match.group(1))}")

        log.info(f"Parsed data: {data}")

        return data

    except Exception as e:
        log.error(
            f"An error has occurred while extracting the data. Error: {e}")
        raise e


def create_line_graph(data):
    """
    Creates a line graph given a data set.

    :param data: The data set to work with.
    :type data: list
    """
    # Set the background color to dark gray
    # Dark gray background
    _, ax = plt.subplots(figsize=(10, 6), facecolor='black')

    # Set the chart background color to dark gray
    ax.set_facecolor('#1F1F1F')

    # Plotting line for retries without markers
    ax.plot(data['time'], data['retries'],
            label='Retries', color='yellow', marker='.')

    # Plotting line for failed endpoints without markers
    ax.plot(data['time'], data['failed'], label='Failed Endpoints',
            color='red', linewidth=2.5, marker='.')

    # Set axis label color to white
    ax.set_xlabel('Time of Execution', color='white')
    ax.set_ylabel('Count', color='white')  # Set axis label color to white
    ax.set_title('Failed Endpoints and Retries Over Time',
                 color='white')  # Set title color to white

    # Set x-axis tick label color to white
    ax.tick_params(axis='x', colors='white')
    # Set y-axis tick label color to white
    ax.tick_params(axis='y', colors='white')

    # Add grid lines to the y-axis
    ax.yaxis.grid(color='gray', linestyle=':', linewidth=0.5)

    # Customize x-axis ticks for better readability
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    ax.legend()

    plt.tight_layout()
    plt.savefig(image_path)
    plt.close()


# Run if being ran directly and not imported
if __name__ == '__main__':
    log_data = parse_log_file(log_file_path)
    log.debug(log_data)  # Print the parsed data for debugging
    create_line_graph(log_data)
