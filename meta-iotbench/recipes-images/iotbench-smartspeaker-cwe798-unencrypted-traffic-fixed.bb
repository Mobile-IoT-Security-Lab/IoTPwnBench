# INTENTIONALLY INSECURE TELNET LAB — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc
require recipes-images/iotbench-unencrypted-traffic.inc

SUMMARY = "IoTBench corrected twin - smartspeaker, weak Telnet unencrypted traffic (CWE-798/287/276)"
DESCRIPTION = "Corrected twin of iotbench-smartspeaker-cwe798-unencrypted-traffic. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
