# Native sudo maintenance-report lab; explicit test builds only.
require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
require recipes-images/iotbench-sudo-environment.inc

SUMMARY = "IoTBench corrected twin - smartbulb, bad sudo environment policy (CWE-798)"
DESCRIPTION = "Corrected twin of iotbench-smartbulb-cwe798-sudo-environment. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
