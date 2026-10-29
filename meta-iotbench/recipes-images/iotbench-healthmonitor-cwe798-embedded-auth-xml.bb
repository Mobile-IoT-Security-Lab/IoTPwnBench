require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "xml"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - healthmonitor, CWE-798 embedded auth xml"
