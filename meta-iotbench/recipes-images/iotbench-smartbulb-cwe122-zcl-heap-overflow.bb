require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc

SUMMARY = "IoTBench target - smart bulb, CWE-122 ZCL heap overflow"
DESCRIPTION = "Smart bulb firmware with a heap overflow in its emulated Zigbee commissioning parser."

IOTBENCH_CWE = "CWE-122"
IOTBENCH_VULN_INSTALL = "cwe122-smartbulb-zcl-overflow"
