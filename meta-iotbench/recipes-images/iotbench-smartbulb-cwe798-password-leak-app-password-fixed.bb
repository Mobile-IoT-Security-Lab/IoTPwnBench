require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "app-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench corrected twin - smartbulb, CWE-798 password leak app-password"
DESCRIPTION = "Corrected twin of iotbench-smartbulb-cwe798-password-leak-app-password. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
