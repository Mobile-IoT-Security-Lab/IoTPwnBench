require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc

SUMMARY = "IoTBench corrected twin - smart speaker, CWE-122 ID3 heap overflow"
DESCRIPTION = "Corrected twin of iotbench-smartspeaker-cwe122-id3-heap-overflow. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-122"
IOTBENCH_VULN_INSTALL = "cwe122-smartspeaker-id3-overflow-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
