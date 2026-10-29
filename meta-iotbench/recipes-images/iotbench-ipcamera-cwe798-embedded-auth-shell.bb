require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "shell"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench fixture - ipcamera, CWE-798 embedded auth shell"
