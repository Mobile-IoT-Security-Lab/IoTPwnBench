require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench corrected twin - PLC, CWE-121 Modbus stack overflow"
DESCRIPTION = "Corrected twin of iotbench-plc-cwe121-modbus-stack-overflow. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-121"
IOTBENCH_VULN_INSTALL = "cwe121-plc-modbus-stack-overflow-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
