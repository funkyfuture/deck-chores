#!/bin/sh

for i in $(seq $COUNT); do
    echo "beep $(date)" >> /receiver.txt
    sleep $DELAY
done

echo "Beeped ${COUNT} times"
