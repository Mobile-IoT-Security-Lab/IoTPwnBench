require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-78 Bash command injection"
DESCRIPTION = "Router firmware with a shell diagnostic script that evals user input."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-bash-command-injection"
