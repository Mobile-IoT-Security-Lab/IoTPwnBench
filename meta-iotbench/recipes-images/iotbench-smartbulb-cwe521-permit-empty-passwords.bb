require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
require recipes-images/iotbench-permit-empty-passwords.inc

SUMMARY = "IoTBench target - smartbulb, CWE-521 SSH empty-password policy"
DESCRIPTION = "Synthetic PermitEmptyPasswords policy and dashboard diagnostic; no SSH daemon or empty-password accounts."
