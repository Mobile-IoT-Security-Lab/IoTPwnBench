require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-276 bad chown rights"
DESCRIPTION = "Router firmware with a privileged policy file incorrectly owned by the web service account."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-bad-chown-rights"
