require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-78 OS command injection (ping diagnostic)"
DESCRIPTION = "Router firmware whose ping diagnostic passes unsanitized input to \
a shell command, exposing OS command injection (CWE-78)."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-os-command-injection"
