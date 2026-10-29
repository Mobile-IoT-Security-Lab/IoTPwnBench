require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "native"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - smartspeaker, CWE-798 embedded auth native"
