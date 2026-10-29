#!/bin/sh
# Build the firmware catalog. The catalog is the set of
# recipes-images/iotbench-*.bb recipes; MACHINES selects the architectures.
#   MACHINES  space-separated list (default: qemuarm64)
#             e.g. MACHINES="qemuarm64 qemuarm qemux86-64 qemux86 qemumips"
set -eu

cd "$(dirname -- "$0")/.."
MACHINES="${MACHINES:-qemuarm64}"

for machine in ${MACHINES}; do
    for bb in meta-iotbench/recipes-images/iotbench-*.bb; do
        firmware=$(basename "$bb" .bb)
        firmware=${firmware#iotbench-}
        service_flag=""
        case "$firmware" in
            *-cwe276-bad-write-rights) service_flag=IOTBENCH_ENABLE_FTP_WRITE_FIXTURE ;;
            *-cwe798-unencrypted-traffic) service_flag=IOTBENCH_ENABLE_TELNET_FIXTURE ;;
            *-cwe798-sudo-environment) service_flag=IOTBENCH_ENABLE_SUDO_ENV_FIXTURE ;;
        esac
        if [ -n "$service_flag" ]; then
            if [ "$(printenv "$service_flag" || true)" != 1 ]; then
                echo "Skipping opt-in service fixture ${firmware} (set ${service_flag}=1 to include)"
                continue
            fi
            YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm \
                -e "$service_flag=1" \
                -e IOTBENCH_BUILD_MODE="${IOTBENCH_BUILD_MODE:-fixture}" yocto
            continue
        fi
        case "$firmware" in
            *-cwe502-java-deserialization)
                if [ "${IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE:-0}" != 1 ]; then
                    echo "Skipping opt-in Java deserialization fixture ${firmware}"
                    continue
                fi
                YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm \
                    -e IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE=1 \
                    -e IOTBENCH_BUILD_MODE="${IOTBENCH_BUILD_MODE:-fixture}" yocto
                continue
                ;;
            *-cwe078-java-os-command-injection|*-cwe077-java-app-command-injection)
                if [ "${IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE:-0}" != 1 ]; then
                    echo "Skipping opt-in Java command fixture ${firmware}"
                    continue
                fi
                YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm \
                    -e IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1 \
                    -e IOTBENCH_BUILD_MODE="${IOTBENCH_BUILD_MODE:-fixture}" yocto
                continue
                ;;
            *-cwe061-native-symlink-following)
                if [ "${IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE:-0}" != 1 ]; then
                    echo "Skipping opt-in native symlink fixture ${firmware}"
                    continue
                fi
                YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm \
                    -e IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE=1 \
                    -e IOTBENCH_BUILD_MODE="${IOTBENCH_BUILD_MODE:-fixture}" yocto
                continue
                ;;
            *-cwe020-native-connection-string)
                if [ "${IOTBENCH_ENABLE_CONNECTION_FIXTURE:-0}" != 1 ]; then
                    echo "Skipping opt-in native connection fixture ${firmware}"
                    continue
                fi
                YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm \
                    -e IOTBENCH_ENABLE_CONNECTION_FIXTURE=1 \
                    -e IOTBENCH_BUILD_MODE="${IOTBENCH_BUILD_MODE:-fixture}" yocto
                continue
                ;;
            *-cwe787-native-buffer-overflow)
                if [ "${IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE:-0}" != 1 ]; then
                    echo "Skipping opt-in native buffer fixture ${firmware}"
                    continue
                fi
                YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm \
                    -e IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE=1 \
                    -e IOTBENCH_BUILD_MODE="${IOTBENCH_BUILD_MODE:-fixture}" \
                    -e IOTBENCH_NATIVE_BUFFER_ASAN="${IOTBENCH_NATIVE_BUFFER_ASAN:-0}" yocto
                continue
                ;;
            *-cwe022-native-path-traversal|*-cwe020-native-filename-validation)
                if [ "${IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE:-0}" != 1 ]; then
                    echo "Skipping opt-in native path fixture ${firmware}"
                    continue
                fi
                YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm \
                    -e IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE=1 \
                    -e IOTBENCH_BUILD_MODE="${IOTBENCH_BUILD_MODE:-fixture}" yocto
                continue
                ;;
            *-cwe???-apache-web)
                if [ "${IOTBENCH_ENABLE_APACHE_FIXTURE:-0}" != 1 ]; then
                    echo "Skipping opt-in Apache fixture ${firmware}"
                    continue
                fi
                YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm \
                    -e IOTBENCH_ENABLE_APACHE_FIXTURE=1 \
                    -e IOTBENCH_BUILD_MODE="${IOTBENCH_BUILD_MODE:-fixture}" yocto
                continue
                ;;
            *-cwe798-embedded-auth-*)
                if [ "${IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE:-0}" != 1 ]; then
                    echo "Skipping opt-in embedded authentication fixture ${firmware}"
                    continue
                fi
                YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm \
                    -e IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE=1 \
                    -e IOTBENCH_BUILD_MODE="${IOTBENCH_BUILD_MODE:-fixture}" yocto
                continue
                ;;
            *-cwe022-rest-internal-files)
                if [ "${IOTBENCH_ENABLE_REST_FIXTURE:-0}" != 1 ]; then
                    echo "Skipping opt-in synthetic REST fixture ${firmware}"
                    continue
                fi
                YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm \
                    -e IOTBENCH_ENABLE_REST_FIXTURE=1 \
                    -e IOTBENCH_BUILD_MODE="${IOTBENCH_BUILD_MODE:-fixture}" yocto
                continue
                ;;
            *-cwe798-password-leak-*)
                if [ "${IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE:-0}" != 1 ]; then
                    echo "Skipping opt-in Password Leak fixture ${firmware}"
                    continue
                fi
                YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm \
                    -e IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE=1 \
                    -e IOTBENCH_BUILD_MODE="${IOTBENCH_BUILD_MODE:-fixture}" yocto
                continue
                ;;
            *-cwe088-cronjob-wildcard-injection)
                if [ "${IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE:-0}" != 1 ]; then
                    echo "Skipping opt-in synthetic cron wildcard fixture ${firmware} (set IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE=1 to include)"
                    continue
                fi
                YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm \
                    -e IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE=1 \
                    -e IOTBENCH_BUILD_MODE="${IOTBENCH_BUILD_MODE:-fixture}" yocto
                continue
                ;;
        esac
        echo "=== Building ${firmware} for ${machine} ==="
        YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm yocto
    done
done

echo "All firmwares built. See deploy-images/<firmware>/<machine>/."
