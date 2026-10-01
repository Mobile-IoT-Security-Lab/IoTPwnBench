require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-798 sudo LD_PRELOAD code injection"
DESCRIPTION = "Router firmware with a sudo rule that preserves LD_PRELOAD for a root command."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-ld-preload-sudo"
