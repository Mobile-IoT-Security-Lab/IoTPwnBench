require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc

SUMMARY = "IoTBench target - IP camera, CWE-22 recording path traversal"
DESCRIPTION = "IP camera firmware whose recording-export CGI reads files outside the recording directory."

IOTBENCH_CWE = "CWE-22"
IOTBENCH_VULN_INSTALL = "cwe022-ipcamera-recording-traversal"
