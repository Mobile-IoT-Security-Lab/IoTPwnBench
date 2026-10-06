require recipes-images/iotbench-image.inc
require recipes-images/iotbench-bad-sudo-rights.inc
require recipes-devices/smartbulb/device-smartbulb.inc

SUMMARY = "IoTBench target - smartbulb, CWE-22 bad sudo rights path traversal"
IOTBENCH_CWE = "CWE-22"
IOTBENCH_VULN_INSTALL = "cwe022-bad-sudo-rights"
