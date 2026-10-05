require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench target - PLC, CWE-78 Modbus maintenance command injection"
DESCRIPTION = "PLC firmware whose vendor-style Modbus project registers pass an attacker-controlled project name to a privileged shell command."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-modbus-command-injection"
