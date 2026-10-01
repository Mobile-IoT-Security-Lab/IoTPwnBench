require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-276 leaked private key"
DESCRIPTION = "Router firmware with a world-readable private key exposed below the web document root."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-leaked-private-key"
