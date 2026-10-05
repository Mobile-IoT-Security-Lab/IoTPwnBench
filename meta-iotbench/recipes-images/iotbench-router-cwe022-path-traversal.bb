require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-22 path traversal"
DESCRIPTION = "Router firmware with a global Lighttpd fallback vulnerable to double-decoded path traversal."

IOTBENCH_CWE = "CWE-22"
IOTBENCH_VULN_INSTALL = "cwe022-path-traversal"
