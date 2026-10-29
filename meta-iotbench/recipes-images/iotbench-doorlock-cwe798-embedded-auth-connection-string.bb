require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "connection-string"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - doorlock, CWE-798 embedded auth connection-string"
