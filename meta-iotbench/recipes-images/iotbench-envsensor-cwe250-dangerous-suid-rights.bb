require recipes-images/iotbench-image.inc
require recipes-images/iotbench-dangerous-suid-rights.inc
require recipes-devices/envsensor/device-envsensor.inc

SUMMARY = "IoTBench target - envsensor, CWE-250 dangerous SUID rights"
IOTBENCH_CWE = "CWE-250"
IOTBENCH_VULN_INSTALL = "cwe250-dangerous-suid-rights"
