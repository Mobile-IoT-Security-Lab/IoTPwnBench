require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc
require recipes-images/iotbench-permit-empty-passwords.inc

SUMMARY = "IoTBench target - healthmonitor, CWE-521 SSH empty-password policy"
DESCRIPTION = "Synthetic PermitEmptyPasswords policy and dashboard diagnostic; no SSH daemon or empty-password accounts."
