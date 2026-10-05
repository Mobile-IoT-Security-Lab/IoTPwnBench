require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc

SUMMARY = "IoTBench target - thermostat, CWE-276 anonymous FTP login allowed"
DESCRIPTION = "thermostat firmware with permissive default FTP access exposing maintenance backups without credentials."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-allow-anonymous-login"
