require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc

SUMMARY = "IoTBench corrected twin - IP camera, CWE-22 recording path traversal"
DESCRIPTION = "Corrected twin of iotbench-ipcamera-cwe022-recording-path-traversal. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-22"
IOTBENCH_VULN_INSTALL = "cwe022-ipcamera-recording-traversal-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
