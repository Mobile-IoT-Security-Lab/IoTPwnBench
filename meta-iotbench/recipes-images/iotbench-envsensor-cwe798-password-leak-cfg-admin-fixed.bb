require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "cfg-admin"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench corrected twin - envsensor, CWE-798 password leak cfg-admin"
DESCRIPTION = "Corrected twin of iotbench-envsensor-cwe798-password-leak-cfg-admin. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
