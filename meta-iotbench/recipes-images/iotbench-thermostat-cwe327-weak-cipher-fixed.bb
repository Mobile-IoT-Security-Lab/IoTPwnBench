require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc

SUMMARY = "IoTBench corrected twin - thermostat, CWE-327 weak 3DES cipher"
DESCRIPTION = "Corrected twin of iotbench-thermostat-cwe327-weak-cipher. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-327"
IOTBENCH_VULN_INSTALL = "cwe327-weak-cipher-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
