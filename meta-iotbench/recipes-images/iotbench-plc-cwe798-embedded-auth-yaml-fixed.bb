require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "yaml"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench corrected twin - plc, CWE-798 embedded auth yaml"
DESCRIPTION = "Corrected twin of iotbench-plc-cwe798-embedded-auth-yaml. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
