# INTENTIONALLY INSECURE TELNET LAB — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc
require recipes-images/iotbench-unencrypted-traffic.inc

SUMMARY = "IoTBench target - doorlock, weak Telnet unencrypted traffic (CWE-798/287/276)"
DESCRIPTION = "Native Telnet maintenance login; explicit test builds only, private loopback network, unprivileged system account."
