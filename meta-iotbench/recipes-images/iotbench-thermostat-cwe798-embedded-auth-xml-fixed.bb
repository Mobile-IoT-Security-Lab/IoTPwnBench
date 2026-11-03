require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc
IOTBENCH_EMBEDDED_AUTH_VARIANT = "xml"
require recipes-images/iotbench-embedded-auth.inc

SUMMARY = "IoTBench corrected twin - thermostat, CWE-798 embedded auth xml"
DESCRIPTION = "Corrected twin of iotbench-thermostat-cwe798-embedded-auth-xml. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
