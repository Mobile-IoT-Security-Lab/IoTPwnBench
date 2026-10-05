require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc

SUMMARY = "IoTBench target - health monitor, CWE-200 memory disclosure"
DESCRIPTION = "Health monitor firmware exposing unauthenticated reads from a simulated device memory region."

IOTBENCH_CWE = "CWE-200"
IOTBENCH_VULN_INSTALL = "cwe200-healthmonitor-memory-disclosure"
