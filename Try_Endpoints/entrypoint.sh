#!/bin/sh
service cron start
echo "Gathering data..."
python3 endpointTests.py > /var/log/endpointTests.log 2>&1
python3 updateGraph.py > /var/log/updateGraph.log 2>&1
echo "Starting webserver"
python3 webserver.py > /var/log/webserver.log 2>&1 &
echo "Ready to rock and roll!"
tail -f /dev/null
