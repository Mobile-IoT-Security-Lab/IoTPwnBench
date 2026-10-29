require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "ini"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - router, CWE-798 embedded auth ini"
