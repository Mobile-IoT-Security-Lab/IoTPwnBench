FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
# Required only by explicitly enabled Apache fixture builds.
SRC_URI:append = "${@' file://apache-fixture.cfg' if d.getVar('IOTBENCH_ENABLE_APACHE_FIXTURE') == '1' and d.getVar('IOTBENCH_BUILD_MODE') == 'fixture' else ''}"
# Namespace isolation is a runtime prerequisite for native path and symlink tests.
SRC_URI:append = "${@' file://native-path-fixture.cfg' if (d.getVar('IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE') == '1' or d.getVar('IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE') == '1') and d.getVar('IOTBENCH_BUILD_MODE') == 'fixture' else ''}"
# Native connection fixtures fail closed unless syscall filtering is available.
SRC_URI:append = "${@' file://connection-fixture.cfg' if d.getVar('IOTBENCH_ENABLE_CONNECTION_FIXTURE') == '1' and d.getVar('IOTBENCH_BUILD_MODE') == 'fixture' else ''}"
# Java stdin/JAR tests use the same unprivileged namespace prerequisites.
SRC_URI:append = "${@' file://native-path-fixture.cfg' if d.getVar('IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE') == '1' and d.getVar('IOTBENCH_BUILD_MODE') == 'fixture' else ''}"
SRC_URI:append = "${@' file://native-path-fixture.cfg' if d.getVar('IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE') == '1' and d.getVar('IOTBENCH_BUILD_MODE') == 'fixture' else ''}"
