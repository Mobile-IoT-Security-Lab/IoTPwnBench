require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc

SUMMARY = "IoTBench target - smartbulb, CWE-276 SSH root login permitted"
DESCRIPTION = "smartbulb firmware with a permissive default SSH policy allowing direct root password login."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-permit-root-login"
