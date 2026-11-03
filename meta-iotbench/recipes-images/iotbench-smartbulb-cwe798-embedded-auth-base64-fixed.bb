require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "base64"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench corrected twin - smartbulb, CWE-798 embedded auth base64"
DESCRIPTION = "Corrected twin of iotbench-smartbulb-cwe798-embedded-auth-base64. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
