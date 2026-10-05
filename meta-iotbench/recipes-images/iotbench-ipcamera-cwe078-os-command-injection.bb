require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc

SUMMARY = "IoTBench target - IP camera, CWE-78 PTZ CGI command injection"
DESCRIPTION = "IP camera firmware whose PTZ CGI passes an HTTP preset parameter to a shell command without neutralizing metacharacters."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-ipcamera-ptz-command-injection"
