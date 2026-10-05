require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc

SUMMARY = "IoTBench target - healthmonitor, CWE-276 anonymous FTP login allowed"
DESCRIPTION = "healthmonitor firmware with permissive default FTP access exposing maintenance backups without credentials."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-allow-anonymous-login"
