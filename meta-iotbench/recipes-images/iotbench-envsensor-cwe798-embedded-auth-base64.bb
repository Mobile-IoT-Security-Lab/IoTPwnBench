require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "base64"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - envsensor, CWE-798 embedded auth base64"
