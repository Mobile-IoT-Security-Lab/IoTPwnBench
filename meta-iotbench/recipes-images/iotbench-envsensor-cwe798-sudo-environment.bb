# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
require recipes-images/iotbench-sudo-environment.inc

SUMMARY = "IoTBench target - envsensor, bad sudo environment policy (CWE-798)"
DESCRIPTION = "One synthetic local sudo environment/diagnostic credential workflow; explicit test builds only."
