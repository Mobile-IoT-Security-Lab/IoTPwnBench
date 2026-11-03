# Native sudo maintenance-report lab; explicit test builds only.
require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc
require recipes-images/iotbench-sudo-environment.inc

SUMMARY = "IoTBench target - smartspeaker, bad sudo environment policy (CWE-798)"
DESCRIPTION = "Native du reads installed device files; a retained environment variable changes reporting units, with an explicit-unit control."
