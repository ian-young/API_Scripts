from datetime import datetime, timedelta
import re

def parse_entry(entry):
    # Use regular expression to extract the time string in the entry
    time_match = re.search(r"(\d{2}/\d{2} \d{2}:\d{2}:\d{2})", entry)
    if time_match:
        time_str = time_match.group(1)
        # Set the year to the current year
        current_year = datetime.now().year
        return datetime.strptime(f"{current_year} {time_str}", "%Y %m/%d %H:%M:%S")

def main():
    # Specify your log file path
    log_file_path = "./endpoint_data.log"

    # Read the file
    with open(log_file_path, "r") as file:
        entries = file.readlines()

    # Get the current time
    current_time = datetime.now()

    # Flag to determine whether to print an entry
    print_entry = False

    # Iterate through entries and check if they are within the last 24 hours
    for entry in entries:
        if "Time of execution" in entry:
            execution_time = parse_entry(entry)
            if execution_time:
                time_difference = current_time - execution_time

                # Check if the entry is within the last 24 hours
                if time_difference < timedelta(days=1):
                    print_entry = True
                    print(entry.strip())  # Print the "Time of execution" entry
                else:
                    print_entry = False
        elif print_entry:
            print(entry.strip())

if __name__ == "__main__":
    main()
