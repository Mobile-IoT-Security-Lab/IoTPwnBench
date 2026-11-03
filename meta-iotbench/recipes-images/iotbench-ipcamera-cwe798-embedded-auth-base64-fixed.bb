require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "base64"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench corrected twin - ipcamera, CWE-798 embedded auth base64"
DESCRIPTION = "Corrected twin of iotbench-ipcamera-cwe798-embedded-auth-base64. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
