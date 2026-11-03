require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc
require recipes-images/iotbench-java-sql-injection.inc

SUMMARY = "IoTBench corrected twin - smartplug, CWE-89 Java JAR SQL injection"
DESCRIPTION = "Corrected twin of iotbench-smartplug-cwe089-java-sql-injection. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-89"
IOTBENCH_VULN_INSTALL = "cwe089-java-sql-injection-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
