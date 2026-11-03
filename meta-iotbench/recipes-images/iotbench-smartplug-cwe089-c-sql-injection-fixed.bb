require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc
require recipes-images/iotbench-c-sql-injection.inc

SUMMARY = "IoTBench corrected twin - smartplug, CWE-89 native C SQL injection"
DESCRIPTION = "Corrected twin of iotbench-smartplug-cwe089-c-sql-injection. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-89"
IOTBENCH_VULN_INSTALL = "cwe089-c-sql-injection-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
