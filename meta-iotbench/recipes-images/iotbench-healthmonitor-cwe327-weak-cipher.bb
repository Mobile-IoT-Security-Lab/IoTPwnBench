require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc

SUMMARY = "IoTBench target - healthmonitor, CWE-327 weak 3DES cipher"
DESCRIPTION = "healthmonitor firmware with device backup encryption using obsolete Triple DES."

IOTBENCH_CWE = "CWE-327"
IOTBENCH_VULN_INSTALL = "cwe327-weak-cipher"
