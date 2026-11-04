require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc
require recipes-images/iotbench-permit-empty-passwords.inc

SUMMARY = "IoTBench corrected twin - smarthub, CWE-521 SSH empty-password policy"
DESCRIPTION = "Corrected twin of iotbench-smarthub-cwe521-permit-empty-passwords. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
