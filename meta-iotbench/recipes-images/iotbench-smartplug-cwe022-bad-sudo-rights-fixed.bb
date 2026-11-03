require recipes-images/iotbench-image.inc
require recipes-images/iotbench-bad-sudo-rights.inc
require recipes-devices/smartplug/device-smartplug.inc

SUMMARY = "IoTBench corrected twin - smartplug, CWE-22 bad sudo rights path traversal"
IOTBENCH_CWE = "CWE-22"
IOTBENCH_VULN_INSTALL = "cwe022-bad-sudo-rights-fixed"
DESCRIPTION = "Corrected twin of iotbench-smartplug-cwe022-bad-sudo-rights. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
