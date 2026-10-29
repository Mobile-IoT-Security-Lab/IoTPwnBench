require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "yaml"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - smarthub, CWE-798 embedded auth yaml"
