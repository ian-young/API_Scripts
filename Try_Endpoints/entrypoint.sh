#!/bin/sh
service cron start
echo "Gathering data..."
python3 endpoint_tests.py > /var/log/endpoint_tests.log 2>&1
echo "--Updating graph with newly acquired data--"
python3 update_graph.py > /var/log/update_graph.log 2>&1
echo "Starting webserver"
python3 webserver.py > /var/log/webserver.log 2>&1 &
echo "Ready to rock and roll!"
tail -f /dev/null
