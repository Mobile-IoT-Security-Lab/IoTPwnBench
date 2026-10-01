require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-416 use after free"
DESCRIPTION = "Router firmware with a C helper that reuses a freed authorization object."

IOTBENCH_CWE = "CWE-416"
IOTBENCH_VULN_INSTALL = "cwe416-use-after-free"
