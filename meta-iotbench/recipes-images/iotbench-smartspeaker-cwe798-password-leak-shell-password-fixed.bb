require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "shell-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench corrected twin - smartspeaker, CWE-798 password leak shell-password"
DESCRIPTION = "Corrected twin of iotbench-smartspeaker-cwe798-password-leak-shell-password. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
