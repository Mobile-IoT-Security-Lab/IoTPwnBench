require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc
require recipes-images/iotbench-permit-empty-passwords.inc

SUMMARY = "IoTBench target - thermostat, CWE-521 SSH empty-password policy"
DESCRIPTION = "Synthetic configuration-only PermitEmptyPasswords fixture; no SSH daemon or empty-password accounts."
