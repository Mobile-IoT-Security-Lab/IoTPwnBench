require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-77 C command injection"
DESCRIPTION = "Router firmware with a C helper that passes user input to system()."

IOTBENCH_CWE = "CWE-77"
IOTBENCH_VULN_INSTALL = "cwe077-c-command-injection"
