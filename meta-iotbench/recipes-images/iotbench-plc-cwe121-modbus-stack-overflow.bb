require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench target - PLC, CWE-121 Modbus stack overflow"
DESCRIPTION = "PLC firmware with a stack overflow in a vendor-specific Modbus project-loader function."

IOTBENCH_CWE = "CWE-121"
IOTBENCH_VULN_INSTALL = "cwe121-plc-modbus-stack-overflow"
