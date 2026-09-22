#!/bin/sh
# Minimal MJPEG stream for the IP camera skeleton (multipart/x-mixed-replace).
printf 'Content-Type: multipart/x-mixed-replace; boundary=iotbenchframe\r\n\r\n'
while :; do
    printf -- '--iotbenchframe\r\nContent-Type: image/jpeg\r\n\r\n'
    cat /www/pages/snapshot.jpg
    printf '\r\n'
    sleep 1
done
