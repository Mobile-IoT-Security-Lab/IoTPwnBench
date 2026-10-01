require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-287 SSH hardcoded backdoor"
DESCRIPTION = "Router firmware with a hardcoded support account and SSH service."

IOTBENCH_CWE = "CWE-287"
IOTBENCH_VULN_INSTALL = "cwe287-ssh-hardcoded-backdoor"
