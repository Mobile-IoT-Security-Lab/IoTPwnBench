require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc
require recipes-images/iotbench-permit-empty-passwords.inc

SUMMARY = "IoTBench target - smarthub, CWE-521 SSH empty-password policy"
DESCRIPTION = "Synthetic configuration-only PermitEmptyPasswords fixture; no SSH daemon or empty-password accounts."
