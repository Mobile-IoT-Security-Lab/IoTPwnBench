require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc

SUMMARY = "IoTBench target - smart speaker, CWE-122 ID3 heap overflow"
DESCRIPTION = "Smart speaker firmware with a heap overflow in its network media metadata parser."

IOTBENCH_CWE = "CWE-122"
IOTBENCH_VULN_INSTALL = "cwe122-smartspeaker-id3-overflow"
