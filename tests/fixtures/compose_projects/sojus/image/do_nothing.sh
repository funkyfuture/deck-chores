#!/bin/sh

while true; do
    sleep 2
    echo "$(date) $(wc -l /receiver.txt)"
done
