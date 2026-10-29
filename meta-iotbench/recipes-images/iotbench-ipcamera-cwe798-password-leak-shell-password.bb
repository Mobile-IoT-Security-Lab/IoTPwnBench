require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "shell-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - ipcamera, CWE-798 password leak shell-password"
