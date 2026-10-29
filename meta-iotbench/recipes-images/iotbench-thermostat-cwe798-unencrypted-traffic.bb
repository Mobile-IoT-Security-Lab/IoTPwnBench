# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc
require recipes-images/iotbench-unencrypted-traffic.inc

SUMMARY = "IoTBench target - thermostat, weak Telnet unencrypted traffic (CWE-798/287/276)"
DESCRIPTION = "One intentionally insecure synthetic Telnet scenario; explicit test builds only, loopback only, no shell."
