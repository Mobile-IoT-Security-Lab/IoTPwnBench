require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc
require recipes-images/iotbench-null-pointer-dereference.inc

SUMMARY = "IoTBench corrected twin - doorlock, CWE-476 native C null pointer dereference"
DESCRIPTION = "Corrected twin of iotbench-doorlock-cwe476-null-pointer-dereference. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-476"
IOTBENCH_VULN_INSTALL = "cwe476-null-pointer-dereference-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
