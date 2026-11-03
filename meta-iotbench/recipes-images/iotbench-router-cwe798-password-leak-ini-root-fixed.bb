require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "ini-root"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench corrected twin - router, CWE-798 password leak ini-root"
DESCRIPTION = "Corrected twin of iotbench-router-cwe798-password-leak-ini-root. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
