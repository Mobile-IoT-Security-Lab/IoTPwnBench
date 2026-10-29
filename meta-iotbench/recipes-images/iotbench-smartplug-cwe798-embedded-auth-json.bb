require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "json"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - smartplug, CWE-798 embedded auth json"
