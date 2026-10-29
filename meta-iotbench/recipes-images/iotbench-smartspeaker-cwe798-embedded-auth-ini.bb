require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "ini"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - smartspeaker, CWE-798 embedded auth ini"
