# INTENTIONALLY INSECURE TELNET LAB — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc
require recipes-images/iotbench-unencrypted-traffic.inc

SUMMARY = "IoTBench corrected twin - smarthub, weak Telnet unencrypted traffic (CWE-798/287/276)"
DESCRIPTION = "Corrected twin of iotbench-smarthub-cwe798-unencrypted-traffic. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
