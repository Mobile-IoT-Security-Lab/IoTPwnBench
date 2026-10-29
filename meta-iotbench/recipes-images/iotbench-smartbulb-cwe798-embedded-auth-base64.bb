require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "base64"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - smartbulb, CWE-798 embedded auth base64"
