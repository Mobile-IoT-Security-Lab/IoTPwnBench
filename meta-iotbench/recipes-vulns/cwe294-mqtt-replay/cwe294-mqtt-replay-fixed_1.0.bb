require recipes-vulns/cwe294-mqtt-replay/cwe294-mqtt-replay_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-294 MQTT replay"
DESCRIPTION = "Corrected twin of cwe294-mqtt-replay. A frame is accepted only with a sequence newer than the last accepted one. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
