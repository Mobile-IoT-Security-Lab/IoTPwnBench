require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc

SUMMARY = "IoTBench corrected twin - smart plug, CWE-862 missing authorization"
DESCRIPTION = "Corrected twin of iotbench-smartplug-cwe862-missing-authorization. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-862"
IOTBENCH_VULN_INSTALL = "cwe862-smartplug-missing-authorization-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
