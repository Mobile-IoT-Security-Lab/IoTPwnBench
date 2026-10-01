require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-89 HTTP SQL injection"
DESCRIPTION = "Router firmware with a vulnerable HTTP login query."

IOTBENCH_CWE = "CWE-89"
IOTBENCH_VULN_INSTALL = "cwe089-http-sqli-auth"
