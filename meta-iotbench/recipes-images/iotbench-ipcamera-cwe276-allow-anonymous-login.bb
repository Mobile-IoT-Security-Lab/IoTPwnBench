require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc

SUMMARY = "IoTBench target - ipcamera, CWE-276 anonymous FTP login allowed"
DESCRIPTION = "ipcamera firmware with permissive default FTP access exposing maintenance backups without credentials."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-allow-anonymous-login"
