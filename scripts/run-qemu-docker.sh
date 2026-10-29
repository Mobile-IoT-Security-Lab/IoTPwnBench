#!/bin/sh
# Run on Linux using QEMU from the existing Yocto build volume.
# No host QEMU/zstd installation is required. Exports are mounted read-only.
# QEMU_DETACH=1 starts in the background; docker stop <printed-name> stops it.
set -eu
cd "$(dirname -- "$0")/.."
FIRMWARE="${FIRMWARE:-router-cwe078-os-command-injection}"
YOCTO_MACHINE="${YOCTO_MACHINE:-qemuarm64}"
name="iotbench-qemu-${FIRMWARE}-${YOCTO_MACHINE}"
case "$FIRMWARE:$YOCTO_MACHINE" in
    *[!a-zA-Z0-9_:-]*) echo "Invalid firmware or machine identifier" >&2; exit 1 ;;
esac
set -- --interactive
if [ "${QEMU_DETACH:-0}" = 1 ]; then
    set -- --detach
elif [ -t 0 ] && [ -t 1 ]; then
    set -- --interactive --tty
fi
if [ -n "${QEMU_TOOLS_IMAGE:-}" ]; then
    test -f "$QEMU_TOOLS_IMAGE"
    set -- "$@" -v "$QEMU_TOOLS_IMAGE:/tools.ext4:ro" -e QEMU_TOOLS_IMAGE=/tools.ext4
fi
echo "QEMU container: $name"
exec docker run --rm "$@" --name "$name" \
    --network host --user 1000:1000 --cap-drop ALL \
    --read-only --tmpfs /tmp:rw,mode=1777 --tmpfs /var/tmp:rw,mode=1777 \
    -v yocto-build:/workdir:ro \
    -v "$PWD/deploy-images:/deploy-images:ro" \
    -v "$PWD/scripts:/scripts:ro" \
    -e FIRMWARE="$FIRMWARE" -e YOCTO_MACHINE="$YOCTO_MACHINE" \
    -e QEMU_HTTP_PORT="${QEMU_HTTP_PORT:-8080}" \
    -e QEMU_MEMORY="${QEMU_MEMORY:-}" -e QEMU_SMP="${QEMU_SMP:-}" \
    -e TMPDIR=/tmp -e QEMU_ROOTFS_DIR=/tmp/rootfs \
    "${YOCTO_BUILDER_IMAGE:-yocto-builder}:6.0.3" bash -euc '
        case "$YOCTO_MACHINE" in
            qemuarm64) qbin=qemu-system-aarch64 ;;
            qemuarm) qbin=qemu-system-arm ;;
            qemux86-64) qbin=qemu-system-x86_64 ;;
            qemux86) qbin=qemu-system-i386 ;;
            qemumips) qbin=qemu-system-mips ;;
            *) echo "Unsupported machine: $YOCTO_MACHINE" >&2; exit 1 ;;
        esac
        for native in /workdir/build/tmp/work/*/qemu-helper-native/*/recipe-sysroot-native; do
            if [ -x "$native/usr/bin/$qbin" ]; then
                export PATH="$native/usr/bin:$PATH"
                export LD_LIBRARY_PATH="$native/usr/lib:$native/lib"
                exec sh /scripts/run-qemu.sh
            fi
        done
        echo "Native QEMU not found; build the selected firmware first." >&2
        exit 1
    '
