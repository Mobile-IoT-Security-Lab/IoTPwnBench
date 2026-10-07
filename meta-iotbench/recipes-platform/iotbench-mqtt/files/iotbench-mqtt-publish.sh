#!/bin/sh
# Publishes the simulated peripheral values to the local MQTT broker.
# Topic layout: iotbench/<device-class>/<peripheral> and .../state (JSON).
set -u

CLASS=device
[ -f /etc/iotbench/device.conf ] && . /etc/iotbench/device.conf 2>/dev/null && CLASS="${DEVICE_CLASS:-device}"
BASE="iotbench/${CLASS}"
BROKER="${MQTT_BROKER:-127.0.0.1}"
PORT="${MQTT_PORT:-1883}"
INTERVAL="${MQTT_INTERVAL:-5}"

while :; do
    if [ -f /run/iotbench/state.env ]; then
        while IFS='=' read -r key value; do
            [ -z "$key" ] && continue
            [ "$key" = "TS" ] && continue
            mosquitto_pub -h "$BROKER" -p "$PORT" -t "${BASE}/${key}" -m "$value" 2>/dev/null || true
        done < /run/iotbench/state.env
        [ -f /run/iotbench/state.json ] && \
            mosquitto_pub -h "$BROKER" -p "$PORT" -t "${BASE}/state" -f /run/iotbench/state.json 2>/dev/null || true
    fi
    sleep "$INTERVAL"
done
