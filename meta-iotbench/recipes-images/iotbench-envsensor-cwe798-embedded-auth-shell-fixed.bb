require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "shell"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench corrected twin - envsensor, CWE-798 embedded auth shell"
DESCRIPTION = "Corrected twin of iotbench-envsensor-cwe798-embedded-auth-shell. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
