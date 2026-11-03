require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc

SUMMARY = "IoTBench corrected twin - smartspeaker, CWE-327 weak 3DES cipher"
DESCRIPTION = "Corrected twin of iotbench-smartspeaker-cwe327-weak-cipher. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-327"
IOTBENCH_VULN_INSTALL = "cwe327-weak-cipher-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
