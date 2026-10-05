require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-276 SSH root login permitted"
DESCRIPTION = "router firmware with a permissive default SSH policy allowing direct root password login."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-permit-root-login"
