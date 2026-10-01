require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-78 service interface command injection"
DESCRIPTION = "Router firmware with a TCP service interface vulnerable to command injection."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-service-interface-injection"
