# Use an official Python runtime as a parent image
FROM debian:stable-slim

# Set the timezone
ENV TZ=:/etc/timezone

# Install necessary packages
RUN apt-get update \
    && apt-get install -y cron python3 python3-pip python3-venv xauth\
    && rm -rf /var/lib/apt/lists/*

# Set up the working directory
WORKDIR /usr/src/app

# Create file for data to be stored
RUN mkdir -p /usr/src/app/data

# Create log directory
RUN mkdir -p /var/log

# Copy the current directory contents into the container
COPY clean_graph.py crontab docker.py endpoint_tests.py entrypoint.sh nginx.conf update_graph.py webserver.py /usr/src/app/
COPY requirements.txt /usr/src/app/

# Create and activate a virtual environment
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Add crontab file
ADD crontab /etc/cron.d/my-cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/my-cron

# Apply cron job
RUN crontab /etc/cron.d/my-cron

# Start the cron job
RUN service cron start

# Apply cron job and make sure the cron process is running
CMD ["cron", "-f"]

# Expose the port for the web server
EXPOSE 5000

# Configure the entry point for the container
RUN chmod +x /usr/src/app/entrypoint.sh

ENTRYPOINT [ "/usr/src/app/entrypoint.sh" ]
