require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "kv-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench corrected twin - smartplug, CWE-798 password leak kv-password"
DESCRIPTION = "Corrected twin of iotbench-smartplug-cwe798-password-leak-kv-password. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
