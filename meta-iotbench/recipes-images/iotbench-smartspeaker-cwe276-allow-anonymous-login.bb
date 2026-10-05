require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc

SUMMARY = "IoTBench target - smartspeaker, CWE-276 anonymous FTP login allowed"
DESCRIPTION = "smartspeaker firmware with permissive default FTP access exposing maintenance backups without credentials."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-allow-anonymous-login"
