require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-798 privileged vi sudo rule"
DESCRIPTION = "Router firmware with a passwordless sudo rule for BusyBox vi."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-vi-privilege-escalation"
