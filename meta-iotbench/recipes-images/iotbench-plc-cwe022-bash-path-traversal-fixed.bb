require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc
require recipes-images/iotbench-bash-path-traversal.inc

SUMMARY = "IoTBench corrected twin - plc, CWE-22 vulnerable Bash path traversal"
DESCRIPTION = "Corrected twin of iotbench-plc-cwe022-bash-path-traversal. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-22"
IOTBENCH_VULN_INSTALL = "cwe022-bash-path-traversal-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
