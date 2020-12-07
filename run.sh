#!/bin/sh
cd `dirname $0`
# btmon > log.txt &
btmon| ./server.py &
while true; do hciconfig hci0 down; hciconfig hci0 up ;timeout 5 hcitool lescan; sleep 60 ;done > /dev/null
