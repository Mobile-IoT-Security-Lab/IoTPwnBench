require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc

SUMMARY = "IoTBench target - ipcamera, CWE-276 SSH root login permitted"
DESCRIPTION = "ipcamera firmware with a permissive default SSH policy allowing direct root password login."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-permit-root-login"
