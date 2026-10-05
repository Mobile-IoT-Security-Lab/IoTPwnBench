require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc

SUMMARY = "IoTBench target - thermostat, CWE-276 SSH root login permitted"
DESCRIPTION = "thermostat firmware with a permissive default SSH policy allowing direct root password login."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-permit-root-login"
