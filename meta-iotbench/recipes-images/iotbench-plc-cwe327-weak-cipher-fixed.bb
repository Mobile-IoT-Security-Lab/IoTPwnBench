require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench corrected twin - plc, CWE-327 weak 3DES cipher"
DESCRIPTION = "Corrected twin of iotbench-plc-cwe327-weak-cipher. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-327"
IOTBENCH_VULN_INSTALL = "cwe327-weak-cipher-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
