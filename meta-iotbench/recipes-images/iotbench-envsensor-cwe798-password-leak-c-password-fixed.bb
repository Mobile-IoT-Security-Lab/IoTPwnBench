require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "c-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench corrected twin - envsensor, CWE-798 password leak c-password"
DESCRIPTION = "Corrected twin of iotbench-envsensor-cwe798-password-leak-c-password. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
