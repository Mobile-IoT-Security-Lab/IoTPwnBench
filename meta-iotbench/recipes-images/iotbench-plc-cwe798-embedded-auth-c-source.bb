require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "c-source"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - plc, CWE-798 embedded auth c-source"
