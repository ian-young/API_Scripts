#!/bin/bash
# To be ran with 0 2 * * 0 /bin/bash /path/to/manage_pihole_logs.sh

# Path to Pi-hole logs directory
LOGS_DIR="/var/log/pihole"
LIGHTTPD_DIR="/var/log/lighttpd"

# Function to log messages
log_message() {
    logger -t "Pi-hole Management Script" "$1"
}

# Truncate audit log
log_message "Truncating audit log..."
truncate -s 0 "${LOGS_DIR}/audit.log"

# Truncate graphing log
log_message "Truncating graphing log..."
truncate -s 0 "${LOGS_DIR}/gravity.log"

log_message "Logs truncated successfully."

# Delete log files older than one month
log_message "Deleting log files older than one month..."
find "${LOGS_DIR}" -name "*.log" -type f -mtime +30 -exec rm {} \;

log_message "Old log files deleted successfully."

# Delete warning logs older than one week
log_message "Deleting warning logs older than one week..."
find "${LIGHTTPD_DIR}" -name "error.log*" -type f -mtime +7 -exec rm {} \;

log_message "Old warning logs deleted successfully."

# Update the pihole software
pihole -up

# Update pip and its modules
python3 -m pip install --upgrade pip >> /dev/null 
pip list --outdated --format=columns | tail -n +3 | cut -d ' ' -f 1 | xargs -n1 pip install -U