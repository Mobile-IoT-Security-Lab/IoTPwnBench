require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench target - plc, CWE-276 anonymous FTP login allowed"
DESCRIPTION = "plc firmware with permissive default FTP access exposing maintenance backups without credentials."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-allow-anonymous-login"
