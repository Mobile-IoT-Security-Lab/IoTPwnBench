require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-276 anonymous FTP login allowed"
DESCRIPTION = "router firmware with permissive default FTP access exposing maintenance backups without credentials."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-allow-anonymous-login"
