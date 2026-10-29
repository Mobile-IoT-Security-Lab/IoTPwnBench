require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "xml"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - thermostat, CWE-798 embedded auth xml"
