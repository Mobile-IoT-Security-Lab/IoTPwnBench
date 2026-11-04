require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc

SUMMARY = "IoTBench corrected twin - thermostat, CWE-294 command replay"
DESCRIPTION = "Corrected twin of iotbench-thermostat-cwe294-command-replay. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-294"
IOTBENCH_VULN_INSTALL = "cwe294-mqtt-replay-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
