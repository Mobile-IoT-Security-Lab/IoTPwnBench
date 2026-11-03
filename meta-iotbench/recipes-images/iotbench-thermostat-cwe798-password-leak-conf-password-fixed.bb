require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "conf-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench corrected twin - thermostat, CWE-798 password leak conf-password"
DESCRIPTION = "Corrected twin of iotbench-thermostat-cwe798-password-leak-conf-password. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
