require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "env-db"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench corrected twin - healthmonitor, CWE-798 password leak env-db"
DESCRIPTION = "Corrected twin of iotbench-healthmonitor-cwe798-password-leak-env-db. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
