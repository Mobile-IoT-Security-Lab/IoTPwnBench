require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc

SUMMARY = "IoTBench target - smart hub, CWE-121 database stack overflow"
DESCRIPTION = "Smart hub firmware whose HTTP database lookup overflows a fixed stack buffer."

IOTBENCH_CWE = "CWE-121"
IOTBENCH_VULN_INSTALL = "cwe121-smarthub-stack-overflow"
