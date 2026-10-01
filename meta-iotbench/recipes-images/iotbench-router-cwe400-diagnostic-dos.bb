require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-400 diagnostic denial of service"
DESCRIPTION = "Router firmware with a diagnostic helper that allocates attacker-selected memory."

IOTBENCH_CWE = "CWE-400"
IOTBENCH_VULN_INSTALL = "cwe400-diagnostic-dos"
