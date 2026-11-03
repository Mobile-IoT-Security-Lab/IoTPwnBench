require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench corrected twin - PLC, CWE-78 Modbus maintenance command injection"
DESCRIPTION = "Corrected twin of iotbench-plc-cwe078-os-command-injection. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-modbus-command-injection-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
