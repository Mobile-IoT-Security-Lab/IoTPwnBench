# Minimal broker for the lab: drop TLS and websockets to cut dependencies.
# The upstream Type=notify service needs systemd support to finish starting
# and release the dependent IoTBench telemetry publisher.
PACKAGECONFIG = "${@bb.utils.filter('DISTRO_FEATURES', 'systemd', d)}"
