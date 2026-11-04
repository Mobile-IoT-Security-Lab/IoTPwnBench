require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "c-source"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench corrected twin - smartplug, CWE-798 embedded auth c-source"
DESCRIPTION = "Corrected twin of iotbench-smartplug-cwe798-embedded-auth-c-source. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
