require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
require recipes-images/iotbench-permit-empty-passwords.inc

SUMMARY = "IoTBench target - smartbulb, CWE-521 SSH empty-password policy"
DESCRIPTION = "Synthetic configuration-only PermitEmptyPasswords fixture; no SSH daemon or empty-password accounts."
