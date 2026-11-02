# Enable the native Telnet daemon only in the explicitly selected Telnet lab.
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
IOTBENCH_ENABLE_TELNET_FIXTURE ?= "0"
SRC_URI:append = "${@' file://iotbench-telnet.cfg' if d.getVar('IOTBENCH_ENABLE_TELNET_FIXTURE') == '1' and d.getVar('IOTBENCH_BUILD_MODE') == 'fixture' else ''}"
