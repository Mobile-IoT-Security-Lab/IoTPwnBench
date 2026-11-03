require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc

SUMMARY = "IoTBench corrected twin - health monitor, CWE-200 memory disclosure"
DESCRIPTION = "Corrected twin of iotbench-healthmonitor-cwe200-memory-disclosure. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-200"
IOTBENCH_VULN_INSTALL = "cwe200-healthmonitor-memory-disclosure-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
