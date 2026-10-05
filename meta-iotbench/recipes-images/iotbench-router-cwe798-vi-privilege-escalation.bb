require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-798 hardcoded maintenance credential"
DESCRIPTION = "Router firmware with a shared maintenance password embedded in the image; the account can invoke the vendor editor workflow."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-vi-privilege-escalation"

# Password: iotbench. Every firmware instance carries the same credential.
EXTRA_USERS_PARAMS:append = " usermod -p '\$6\$iotbench\$EhBo2e24buhGDuzZQTBFBg58AJA3.wI.gOIVDU0A91zC8jaiqiIY//.WW6PfQB6Jf4qnaLLCU7BFkXvuKT1XG1' -s /bin/sh routerweb;"
