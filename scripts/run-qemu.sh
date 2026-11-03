#!/bin/sh
# Boot an exported IoTBench firmware with QEMU on the host.
# Requires the matching qemu-system-* binary and zstd.
#   FIRMWARE        firmware id under deploy-images/ (default: router-cwe078-os-command-injection)
#   YOCTO_MACHINE   qemuarm64 (default) | qemuarm | qemux86-64 | qemux86 | qemumips
#   QEMU_HTTP_PORT  host port forwarded to guest port 80 (default: 8080)
#   QEMU_SSH_PORT   host port forwarded to guest port 22 for SSH scenarios (default: 2222)
#   QEMU_FTP_PORT   host port forwarded to guest port 21 for anonymous FTP (default: 2121)
#                   Passive data ports 30000-30009 are forwarded unchanged.
#   QEMU_SERVICE_PORT host port forwarded to guest port 9090 (default: 9090)
#   QEMU_MQTT_PORT  host port forwarded to guest port 1883 (default: 1883)
#   QEMU_MODBUS_PORT host port forwarded to guest port 502 (default: 1502)
#   QEMU_ZCL_PORT   host port forwarded to the bulb bridge (default: 17754)
#   QEMU_MEDIA_PORT host port forwarded to the speaker parser (default: 18000)
#   QEMU_HEALTH_PORT host port forwarded to the patient protocol (default: 2575)
#   QEMU_COAP_PORT   host UDP port forwarded to CoAP fixtures (default: 5683)
#   QEMU_ACCEL      tcg (default), or kvm/hvf where host and guest arch match
#   QEMU_CPU        override the emulated CPU
#   QEMU_PERSIST    1 keeps guest writes in the .ext4 across boots (power off the
#                   guest cleanly). Default 0 boots a throwaway overlay (-snapshot):
#                   the rootfs is always writable and the golden image never
#                   corrupts, but writes are dropped when QEMU exits.
set -eu

FIRMWARE="${FIRMWARE:-router-cwe078-os-command-injection}"
MACHINE="${YOCTO_MACHINE:-qemuarm64}"
IMAGE="iotbench-${FIRMWARE}"
DEPLOY_DIR="$(dirname -- "$0")/../deploy-images/${FIRMWARE}/${MACHINE}"
ROOTFS="${DEPLOY_DIR}/${IMAGE}-${MACHINE}.rootfs.ext4"
ROOTFS_ARCHIVE="${ROOTFS}.zst"
# A separate writable directory supports read-only exports in Docker.
if [ -n "${QEMU_ROOTFS_DIR:-}" ]; then
    mkdir -p "${QEMU_ROOTFS_DIR}"
    ROOTFS="${QEMU_ROOTFS_DIR}/${IMAGE}-${MACHINE}.rootfs.ext4"
fi
HTTP_PORT="${QEMU_HTTP_PORT:-8080}"
SMP=4
MEMORY=256
NETDEV="user,id=net0,hostfwd=tcp:127.0.0.1:${HTTP_PORT}-:80"
EXTRA_ENDPOINT=""

# Serial-only fixtures have no network device or forwarded ports.
case "$FIRMWARE" in
    *-cwe502-java-deserialization)
        NETDEV=""
        MEMORY=1024
        EXTRA_ENDPOINT="Java deserialization fixture: run isolated JAR tests from the guest serial console"
        ;;
    *-cwe078-java-os-command-injection|*-cwe077-java-app-command-injection)
        NETDEV=""
        MEMORY=1024
        EXTRA_ENDPOINT="Java command fixture: run the isolated JAR tests from the guest serial console"
        ;;
    *-cwe061-native-symlink-following)
        NETDEV=""
        EXTRA_ENDPOINT="Native symlink fixture: run the isolated socket tests from the guest serial console"
        ;;
    *-cwe020-native-connection-string)
        NETDEV=""
        EXTRA_ENDPOINT="Native connection fixture: run the stdin tests from the guest serial console"
        ;;
    *-cwe787-native-buffer-overflow)
        NETDEV=""
        EXTRA_ENDPOINT="Native buffer fixture: run the stdin tests from the guest serial console"
        ;;
    *-cwe022-native-path-traversal|*-cwe020-native-filename-validation)
        NETDEV=""
        EXTRA_ENDPOINT="Native path fixture: run the isolated socket tests from the guest serial console"
        ;;
    *-cwe798-password-leak-*)
        NETDEV=""
        EXTRA_ENDPOINT="Password Leak fixture: run the isolated local test from the guest serial console"
        ;;
    *-cwe???-apache-web)
        NETDEV=""
        EXTRA_ENDPOINT="Apache fixture: run tests on guest loopback via the serial console"
        ;;
esac

case "${FIRMWARE}" in
    *-cwe502-java-deserialization) ;;
    *-cwe078-java-os-command-injection|*-cwe077-java-app-command-injection) ;;
    *-cwe061-native-symlink-following) ;;
    *-cwe020-native-connection-string) ;;
    *-cwe787-native-buffer-overflow) ;;
    *-cwe022-native-path-traversal|*-cwe020-native-filename-validation) ;;
    *-cwe???-apache-web) ;;
    *-cwe287-ssh-hardcoded-backdoor)
        SSH_PORT="${QEMU_SSH_PORT:-2222}"
        NETDEV="${NETDEV},hostfwd=tcp:127.0.0.1:${SSH_PORT}-:22"
        EXTRA_ENDPOINT="SSH: ssh -p ${SSH_PORT} support@127.0.0.1"
        ;;
    router-cwe798-ld-preload-sudo|router-cwe798-vi-privilege-escalation)
        SSH_PORT="${QEMU_SSH_PORT:-2222}"
        NETDEV="${NETDEV},hostfwd=tcp:127.0.0.1:${SSH_PORT}-:22"
        EXTRA_ENDPOINT="SSH: ssh -p ${SSH_PORT} routerweb@127.0.0.1"
        ;;
    *-cwe078-service-interface-injection)
        SERVICE_PORT="${QEMU_SERVICE_PORT:-9090}"
        NETDEV="${NETDEV},hostfwd=tcp:127.0.0.1:${SERVICE_PORT}-:9090"
        EXTRA_ENDPOINT="Service interface: 127.0.0.1:${SERVICE_PORT}"
        ;;
    smartplug-*|thermostat-*|smartbulb-*|smarthub-*|envsensor-*|smartspeaker-*|healthmonitor-*|doorlock-*)
        MQTT_PORT="${QEMU_MQTT_PORT:-1883}"
        NETDEV="${NETDEV},hostfwd=tcp:127.0.0.1:${MQTT_PORT}-:1883"
        EXTRA_ENDPOINT="MQTT: 127.0.0.1:${MQTT_PORT}"
        ;;
    plc-*)
        MODBUS_PORT="${QEMU_MODBUS_PORT:-1502}"
        NETDEV="${NETDEV},hostfwd=tcp:127.0.0.1:${MODBUS_PORT}-:502"
        EXTRA_ENDPOINT="Modbus/TCP: 127.0.0.1:${MODBUS_PORT}"
        ;;
esac

# MQTT internal-file fixtures add a broker to HTTP and Modbus device profiles.
case "${FIRMWARE}" in
    router-cwe862-mqtt-internal-files|ipcamera-cwe862-mqtt-internal-files|plc-cwe862-mqtt-internal-files)
        MQTT_PORT="${QEMU_MQTT_PORT:-1883}"
        NETDEV="${NETDEV},hostfwd=tcp:127.0.0.1:${MQTT_PORT}-:1883"
        EXTRA_ENDPOINT="${EXTRA_ENDPOINT}${EXTRA_ENDPOINT:+; }MQTT: 127.0.0.1:${MQTT_PORT}"
        ;;
esac

case "${FIRMWARE}" in
    *-cwe862-coap-internal-files)
        COAP_PORT="${QEMU_COAP_PORT:-5683}"
        NETDEV="${NETDEV},hostfwd=udp:127.0.0.1:${COAP_PORT}-:5683"
        EXTRA_ENDPOINT="${EXTRA_ENDPOINT}${EXTRA_ENDPOINT:+; }CoAP: coap://127.0.0.1:${COAP_PORT}"
        ;;
    *-cwe276-allow-anonymous-login)
        FTP_PORT="${QEMU_FTP_PORT:-2121}"
        NETDEV="${NETDEV},hostfwd=tcp:127.0.0.1:${FTP_PORT}-:21"
        for FTP_DATA_PORT in 30000 30001 30002 30003 30004 30005 30006 30007 30008 30009; do
            NETDEV="${NETDEV},hostfwd=tcp:127.0.0.1:${FTP_DATA_PORT}-:${FTP_DATA_PORT}"
        done
        EXTRA_ENDPOINT="${EXTRA_ENDPOINT}${EXTRA_ENDPOINT:+; }FTP: ftp://127.0.0.1:${FTP_PORT} (anonymous; passive data: 30000-30009)"
        ;;
    *-cwe276-permit-root-login)
        SSH_PORT="${QEMU_SSH_PORT:-2222}"
        NETDEV="${NETDEV},hostfwd=tcp:127.0.0.1:${SSH_PORT}-:22"
        EXTRA_ENDPOINT="${EXTRA_ENDPOINT}${EXTRA_ENDPOINT:+; }SSH: ssh -p ${SSH_PORT} root@127.0.0.1"
        ;;
esac

case "${FIRMWARE}" in
    smartbulb-cwe122-zcl-heap-overflow)
        ZCL_PORT="${QEMU_ZCL_PORT:-17754}"
        NETDEV="${NETDEV},hostfwd=tcp:127.0.0.1:${ZCL_PORT}-:17754"
        EXTRA_ENDPOINT="${EXTRA_ENDPOINT}; ZCL bridge: 127.0.0.1:${ZCL_PORT}"
        ;;
    smartspeaker-cwe122-id3-heap-overflow)
        MEDIA_PORT="${QEMU_MEDIA_PORT:-18000}"
        NETDEV="${NETDEV},hostfwd=tcp:127.0.0.1:${MEDIA_PORT}-:18000"
        EXTRA_ENDPOINT="${EXTRA_ENDPOINT}; media parser: 127.0.0.1:${MEDIA_PORT}"
        ;;
    healthmonitor-cwe200-memory-disclosure)
        HEALTH_PORT="${QEMU_HEALTH_PORT:-2575}"
        NETDEV="${NETDEV},hostfwd=tcp:127.0.0.1:${HEALTH_PORT}-:2575"
        EXTRA_ENDPOINT="${EXTRA_ENDPOINT}; patient protocol: 127.0.0.1:${HEALTH_PORT}"
        ;;
esac

# Per-architecture QEMU parameters.
case "${MACHINE}" in
    qemuarm64)  QBIN=qemu-system-aarch64; QMACH=virt;  QCPU="${QEMU_CPU:-cortex-a57}"; KERNEL=Image;   CONSOLE=ttyAMA0; APPEND_EXTRA="swiotlb=0" ;;
    qemuarm)    QBIN=qemu-system-arm;     QMACH=virt;  QCPU="${QEMU_CPU:-cortex-a15}"; KERNEL=zImage;  CONSOLE=ttyAMA0; APPEND_EXTRA="" ;;
    qemux86-64) QBIN=qemu-system-x86_64;  QMACH=q35;   QCPU="${QEMU_CPU:-}";           KERNEL=bzImage; CONSOLE=ttyS0;   APPEND_EXTRA="" ;;
    qemux86)    QBIN=qemu-system-i386;    QMACH=pc;    QCPU="${QEMU_CPU:-}";           KERNEL=bzImage; CONSOLE=ttyS0;   APPEND_EXTRA="" ;;
    qemumips)   QBIN=qemu-system-mips;    QMACH=malta; QCPU="${QEMU_CPU:-}";           KERNEL=vmlinux; CONSOLE=ttyS0;   APPEND_EXTRA=""; SMP=1 ;;
    *) echo "Unsupported YOCTO_MACHINE: ${MACHINE}" >&2; exit 1 ;;
esac

MEMORY="${QEMU_MEMORY:-$MEMORY}"
SMP="${QEMU_SMP:-$SMP}"

if [ ! -f "${ROOTFS_ARCHIVE}" ]; then
    echo "Firmware not found: ${ROOTFS_ARCHIVE}" >&2
    echo "Build it first: YOCTO_MACHINE=${MACHINE} FIRMWARE=${FIRMWARE} docker compose run --rm yocto" >&2
    exit 1
fi

for required_command in "$QBIN" zstd; do
    if ! command -v "$required_command" >/dev/null 2>&1; then
        echo "Missing host command: $required_command. Install QEMU and zstd before booting." >&2
        exit 1
    fi
done

if [ "${QEMU_PERSIST:-0}" = "1" ]; then
    # Persist writes into the .ext4. Refresh it only from a newer export.
    SNAPSHOT=""
    if [ ! -f "${ROOTFS}" ] || [ "${ROOTFS_ARCHIVE}" -nt "${ROOTFS}" ]; then
        zstd -f -d "${ROOTFS_ARCHIVE}" -o "${ROOTFS}"
    fi
else
    # Always start from a clean base; QEMU writes go to a discarded overlay.
    SNAPSHOT="-snapshot"
    zstd -f -d "${ROOTFS_ARCHIVE}" -o "${ROOTFS}"
fi

CPU_ARG=""
[ -n "${QCPU}" ] && CPU_ARG="-cpu ${QCPU}"

echo "Firmware: ${FIRMWARE} (${MACHINE})"
IP_APPEND="ip=dhcp"
case "${FIRMWARE}" in
    *-cwe120-service-buffer-overflow)
        # The CWE-120 fixture is exclusively local, including during validation.
        set -- -nic none
        IP_APPEND=""
        echo "Local Unix-socket fixture; networking disabled (quit with Ctrl-A, then X)"
        ;;
    *)
        if [ -z "$NETDEV" ]; then
            set -- -nic none
            IP_APPEND=""
        else
            set -- -netdev "${NETDEV}" -device virtio-net-pci,netdev=net0
            echo "Dashboard: http://127.0.0.1:${HTTP_PORT} (quit with Ctrl-A, then X)"
        fi
        ;;
esac
[ -z "${EXTRA_ENDPOINT}" ] || echo "${EXTRA_ENDPOINT}"

# Optional read-only test-tool disk; the exported firmware is unchanged.
if [ -n "${QEMU_TOOLS_IMAGE:-}" ]; then
    test -f "$QEMU_TOOLS_IMAGE"
    set -- "$@" -drive "id=tools,file=${QEMU_TOOLS_IMAGE},if=none,format=raw,readonly=on" -device virtio-blk-pci,drive=tools
fi

# shellcheck disable=SC2086
exec "${QBIN}" \
    -machine "${QMACH},accel=${QEMU_ACCEL:-tcg}" \
    ${CPU_ARG} \
    -smp "${SMP}" \
    -m "${MEMORY}" \
    ${SNAPSHOT} \
    -kernel "${DEPLOY_DIR}/${KERNEL}" \
    -append "root=/dev/vda rw console=${CONSOLE} ${IP_APPEND} ${APPEND_EXTRA}" \
    -drive "id=disk0,file=${ROOTFS},if=none,format=raw" \
    -device virtio-blk-pci,drive=disk0 \
    "$@" \
    -object rng-random,filename=/dev/urandom,id=rng0 \
    -device virtio-rng-pci,rng=rng0 \
    -nographic
