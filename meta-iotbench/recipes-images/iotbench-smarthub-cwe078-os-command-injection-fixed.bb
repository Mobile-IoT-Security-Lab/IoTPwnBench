require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc

SUMMARY = "IoTBench corrected twin - smart hub, CWE-78 MQTT command injection"
DESCRIPTION = "Corrected twin of iotbench-smarthub-cwe078-os-command-injection. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-mqtt-command-injection-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
