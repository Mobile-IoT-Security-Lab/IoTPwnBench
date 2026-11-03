# INTENTIONALLY INSECURE TELNET LAB — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc
require recipes-images/iotbench-unencrypted-traffic.inc

SUMMARY = "IoTBench corrected twin - thermostat, weak Telnet unencrypted traffic (CWE-798/287/276)"
DESCRIPTION = "Corrected twin of iotbench-thermostat-cwe798-unencrypted-traffic. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
