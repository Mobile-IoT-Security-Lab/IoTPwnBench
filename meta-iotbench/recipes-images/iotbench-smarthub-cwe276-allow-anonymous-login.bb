require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc

SUMMARY = "IoTBench target - smarthub, CWE-276 anonymous FTP login allowed"
DESCRIPTION = "smarthub firmware with permissive default FTP access exposing maintenance backups without credentials."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-allow-anonymous-login"
