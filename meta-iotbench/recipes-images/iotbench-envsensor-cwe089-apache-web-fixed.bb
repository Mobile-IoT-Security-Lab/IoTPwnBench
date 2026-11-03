require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc

SUMMARY = "IoTBench corrected twin - envsensor-cwe089-apache-web"
APACHE_FIXTURE_CWE = "089"
require recipes-images/iotbench-apache-fixture.inc
DESCRIPTION = "Corrected twin of iotbench-envsensor-cwe089-apache-web. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
