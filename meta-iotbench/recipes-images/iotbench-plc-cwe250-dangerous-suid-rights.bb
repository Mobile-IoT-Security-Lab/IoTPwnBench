require recipes-images/iotbench-image.inc
require recipes-images/iotbench-dangerous-suid-rights.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench target - plc, CWE-250 dangerous SUID rights"
IOTBENCH_CWE = "CWE-250"
IOTBENCH_VULN_INSTALL = "cwe250-dangerous-suid-rights"
