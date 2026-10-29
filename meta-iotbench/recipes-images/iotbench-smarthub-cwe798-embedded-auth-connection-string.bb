require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "connection-string"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - smarthub, CWE-798 embedded auth connection-string"
