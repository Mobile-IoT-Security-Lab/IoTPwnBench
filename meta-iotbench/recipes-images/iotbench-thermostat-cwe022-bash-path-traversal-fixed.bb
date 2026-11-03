require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc
require recipes-images/iotbench-bash-path-traversal.inc

SUMMARY = "IoTBench corrected twin - thermostat, CWE-22 vulnerable Bash path traversal"
DESCRIPTION = "Corrected twin of iotbench-thermostat-cwe022-bash-path-traversal. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-22"
IOTBENCH_VULN_INSTALL = "cwe022-bash-path-traversal-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
