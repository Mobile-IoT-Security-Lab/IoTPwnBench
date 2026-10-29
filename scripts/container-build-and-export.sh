#!/bin/bash
# Build the selected IoTBench firmware and copy the files run-qemu.sh needs into
# /export/<firmware>/<machine>.
#   FIRMWARE  firmware id; builds iotbench-${FIRMWARE} (default: router-cwe078-os-command-injection)
set -eo pipefail

FIRMWARE="${FIRMWARE:-router-cwe078-os-command-injection}"
IMAGE="iotbench-${FIRMWARE}"

source /opt/yocto/yocto-env.sh
# These service fixtures also need a global BitBake configuration: environment
# variables alone are not visible to recipe parse-time guards.
service_flag=""
case "$FIRMWARE" in
    *-cwe276-bad-write-rights) service_flag=IOTBENCH_ENABLE_FTP_WRITE_FIXTURE ;;
    *-cwe798-unencrypted-traffic) service_flag=IOTBENCH_ENABLE_TELNET_FIXTURE ;;
    *-cwe798-sudo-environment) service_flag=IOTBENCH_ENABLE_SUDO_ENV_FIXTURE ;;
esac
if [[ -n "$service_flag" ]]; then
    [[ "${!service_flag:-0}" == 1 && "${IOTBENCH_BUILD_MODE:-fixture}" == fixture ]] || {
        echo "Service fixture requires matching opt-in and fixture build mode" >&2
        exit 1
    }
    while IFS='=' read -r key value; do
        if [[ "$key" == IOTBENCH_ENABLE_*_FIXTURE && "$key" != "$service_flag" && "$value" != 0 ]]; then
            echo "Service fixture cannot be mixed with another fixture opt-in" >&2
            exit 1
        fi
    done < <(env)
    fixture_conf=$(mktemp /tmp/iotbench-service.XXXXXX.conf)
    trap 'rm -f "$fixture_conf"' EXIT
    printf 'IOTBENCH_BUILD_MODE = "fixture"\n%s = "1"\n' "$service_flag" > "$fixture_conf"
    if [[ "$service_flag" == IOTBENCH_ENABLE_FTP_WRITE_FIXTURE ]]; then
        cat >> "$fixture_conf" <<'FIXTURE_CONF'
DISTRO_FEATURES:append = " pam systemd"
FIXTURE_CONF
    fi
    bitbake -r "$fixture_conf" "${IMAGE}"
elif [[ "${IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE:-0}" == 1 || "$FIRMWARE" == *-cwe502-java-deserialization ]]; then
    [[ "${IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE:-0}" == 1 &&
       "$FIRMWARE" == *-cwe502-java-deserialization &&
       "${IOTBENCH_BUILD_MODE:-fixture}" == fixture ]] || {
        echo "Java deserialization requires its own image, explicit opt-in and fixture mode" >&2
        exit 1
    }
    while IFS='=' read -r key value; do
        if [[ "$key" == IOTBENCH_ENABLE_*_FIXTURE && "$key" != IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE && "$value" != 0 ]]; then
            echo "Java deserialization cannot be mixed with another fixture opt-in" >&2
            exit 1
        fi
    done < <(env)
    fixture_conf=$(mktemp /tmp/iotbench-java-deserialization.XXXXXX.conf)
    trap 'rm -f "$fixture_conf"' EXIT
    cat > "$fixture_conf" <<'FIXTURE_CONF'
IOTBENCH_BUILD_MODE = "fixture"
IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE = "1"
FIXTURE_CONF
    bitbake -r "$fixture_conf" "${IMAGE}"
elif [[ "${IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE:-0}" == 1 ||
      "$FIRMWARE" == *-cwe078-java-os-command-injection || "$FIRMWARE" == *-cwe077-java-app-command-injection ]]; then
    [[ "${IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE:-0}" == 1 &&
       ( "$FIRMWARE" == *-cwe078-java-os-command-injection || "$FIRMWARE" == *-cwe077-java-app-command-injection ) &&
       "${IOTBENCH_BUILD_MODE:-fixture}" == fixture ]] || {
        echo "Java command fixtures require their own image, explicit opt-in and fixture mode" >&2
        exit 1
    }
    while IFS='=' read -r key value; do
        if [[ "$key" == IOTBENCH_ENABLE_*_FIXTURE && "$key" != IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE && "$value" != 0 ]]; then
            echo "Java command fixtures cannot be mixed with another fixture opt-in" >&2
            exit 1
        fi
    done < <(env)
    fixture_conf=$(mktemp /tmp/iotbench-java-command.XXXXXX.conf)
    trap 'rm -f "$fixture_conf"' EXIT
    cat > "$fixture_conf" <<'FIXTURE_CONF'
IOTBENCH_BUILD_MODE = "fixture"
IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE = "1"
FIXTURE_CONF
    bitbake -r "$fixture_conf" "${IMAGE}"
elif [[ "${IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE:-0}" == 1 || "$FIRMWARE" == *-cwe061-native-symlink-following ]]; then
    [[ "${IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE:-0}" == 1 &&
       "$FIRMWARE" == *-cwe061-native-symlink-following &&
       "${IOTBENCH_BUILD_MODE:-fixture}" == fixture ]] || {
        echo "Native symlink fixtures require their own image, explicit opt-in and fixture mode" >&2
        exit 1
    }
    while IFS='=' read -r key value; do
        if [[ "$key" == IOTBENCH_ENABLE_*_FIXTURE && "$key" != IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE && "$value" != 0 ]]; then
            echo "Native symlink fixtures cannot be mixed with another fixture opt-in" >&2
            exit 1
        fi
    done < <(env)
    fixture_conf=$(mktemp /tmp/iotbench-native-symlink.XXXXXX.conf)
    trap 'rm -f "$fixture_conf"' EXIT
    cat > "$fixture_conf" <<'FIXTURE_CONF'
IOTBENCH_BUILD_MODE = "fixture"
IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE = "1"
FIXTURE_CONF
    bitbake -r "$fixture_conf" "${IMAGE}"
elif [[ "${IOTBENCH_ENABLE_CONNECTION_FIXTURE:-0}" == 1 || "$FIRMWARE" == *-cwe020-native-connection-string ]]; then
    [[ "${IOTBENCH_ENABLE_CONNECTION_FIXTURE:-0}" == 1 &&
       "$FIRMWARE" == *-cwe020-native-connection-string &&
       "${IOTBENCH_BUILD_MODE:-fixture}" == fixture ]] || {
        echo "Native connection fixtures require their own image, explicit opt-in and fixture mode" >&2
        exit 1
    }
    while IFS='=' read -r key value; do
        if [[ "$key" == IOTBENCH_ENABLE_*_FIXTURE && "$key" != IOTBENCH_ENABLE_CONNECTION_FIXTURE && "$value" != 0 ]]; then
            echo "Native connection fixtures cannot be mixed with another fixture opt-in" >&2
            exit 1
        fi
    done < <(env)
    fixture_conf=$(mktemp /tmp/iotbench-native-connection.XXXXXX.conf)
    trap 'rm -f "$fixture_conf"' EXIT
    cat > "$fixture_conf" <<'FIXTURE_CONF'
IOTBENCH_BUILD_MODE = "fixture"
IOTBENCH_ENABLE_CONNECTION_FIXTURE = "1"
FIXTURE_CONF
    bitbake -r "$fixture_conf" "${IMAGE}"
elif [[ "${IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE:-0}" == 1 || "$FIRMWARE" == *-cwe787-native-buffer-overflow ]]; then
    [[ "${IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE:-0}" == 1 &&
       "$FIRMWARE" == *-cwe787-native-buffer-overflow &&
       "${IOTBENCH_BUILD_MODE:-fixture}" == fixture ]] || {
        echo "Native buffer fixtures require their own image, explicit opt-in and fixture mode" >&2
        exit 1
    }
    while IFS='=' read -r key value; do
        if [[ "$key" == IOTBENCH_ENABLE_*_FIXTURE && "$key" != IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE && "$value" != 0 ]]; then
            echo "Native buffer fixtures cannot be mixed with another fixture opt-in" >&2
            exit 1
        fi
    done < <(env)
    fixture_conf=$(mktemp /tmp/iotbench-native-buffer.XXXXXX.conf)
    trap 'rm -f "$fixture_conf"' EXIT
    cat > "$fixture_conf" <<'FIXTURE_CONF'
IOTBENCH_BUILD_MODE = "fixture"
IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE = "1"
FIXTURE_CONF
    case "${IOTBENCH_NATIVE_BUFFER_ASAN:-0}" in
        0) ;;
        1) echo 'PACKAGECONFIG:append:pn-cwe787-native-buffer-overflow = " asan"' >> "$fixture_conf" ;;
        *) echo "IOTBENCH_NATIVE_BUFFER_ASAN must be 0 or 1" >&2; exit 1 ;;
    esac
    bitbake -r "$fixture_conf" "${IMAGE}"
elif [[ "${IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE:-0}" == 1 ||
      "$FIRMWARE" == *-cwe022-native-path-traversal || "$FIRMWARE" == *-cwe020-native-filename-validation ]]; then
    [[ "${IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE:-0}" == 1 &&
       ( "$FIRMWARE" == *-cwe022-native-path-traversal || "$FIRMWARE" == *-cwe020-native-filename-validation ) &&
       "${IOTBENCH_BUILD_MODE:-fixture}" == fixture ]] || {
        echo "Native path fixtures require their own image, explicit opt-in and fixture mode" >&2
        exit 1
    }
    while IFS='=' read -r key value; do
        if [[ "$key" == IOTBENCH_ENABLE_*_FIXTURE && "$key" != IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE && "$value" != 0 ]]; then
            echo "Native path fixtures cannot be mixed with another fixture opt-in" >&2
            exit 1
        fi
    done < <(env)
    fixture_conf=$(mktemp /tmp/iotbench-native-path.XXXXXX.conf)
    trap 'rm -f "$fixture_conf"' EXIT
    cat > "$fixture_conf" <<'FIXTURE_CONF'
IOTBENCH_BUILD_MODE = "fixture"
IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE = "1"
FIXTURE_CONF
    case "${IOTBENCH_NATIVE_PATH_ASAN:-0}" in
        0) ;;
        1)
            case "$FIRMWARE" in
                *-cwe022-native-path-traversal) path_package=cwe022-native-path-traversal ;;
                *-cwe020-native-filename-validation) path_package=cwe020-native-filename-validation ;;
            esac
            printf 'PACKAGECONFIG:append:pn-%s = " asan"\n' "$path_package" >> "$fixture_conf"
            ;;
        *) echo "IOTBENCH_NATIVE_PATH_ASAN must be 0 or 1" >&2; exit 1 ;;
    esac
    bitbake -r "$fixture_conf" "${IMAGE}"
elif [[ "${IOTBENCH_ENABLE_APACHE_FIXTURE:-0}" == 1 || "$FIRMWARE" == *-cwe???-apache-web ]]; then
    [[ "${IOTBENCH_ENABLE_APACHE_FIXTURE:-0}" == 1 &&
       "$FIRMWARE" == *-cwe???-apache-web &&
       "${IOTBENCH_BUILD_MODE:-fixture}" == fixture ]] || {
        echo "Apache fixtures require their own image, explicit opt-in and fixture mode" >&2
        exit 1
    }
    while IFS='=' read -r key value; do
        if [[ "$key" == IOTBENCH_ENABLE_*_FIXTURE && "$key" != IOTBENCH_ENABLE_APACHE_FIXTURE && "$value" != 0 ]]; then
            echo "Apache fixtures cannot be mixed with another fixture opt-in" >&2
            exit 1
        fi
    done < <(env)
    fixture_conf=$(mktemp /tmp/iotbench-apache.XXXXXX.conf)
    trap 'rm -f "$fixture_conf"' EXIT
    cat > "$fixture_conf" <<'FIXTURE_CONF'
IOTBENCH_BUILD_MODE = "fixture"
IOTBENCH_ENABLE_APACHE_FIXTURE = "1"
FIXTURE_CONF
    bitbake -r "$fixture_conf" "${IMAGE}"
elif [[ "${IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE:-0}" == 1 ]]; then
    [[ "$FIRMWARE" == *-cwe798-embedded-auth-* &&
       "${IOTBENCH_BUILD_MODE:-fixture}" == fixture &&
       "${IOTBENCH_ENABLE_REST_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_SUDO_ENV_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_TELNET_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_FTP_WRITE_FIXTURE:-0}" != 1 ]] || {
        echo "Embedded auth opt-in requires its own image, fixture mode and no other fixture opt-ins" >&2
        exit 1
    }
    fixture_conf=$(mktemp /tmp/iotbench-embedded-auth.XXXXXX.conf)
    trap 'rm -f "$fixture_conf"' EXIT
    cat > "$fixture_conf" <<'FIXTURE_CONF'
IOTBENCH_BUILD_MODE = "fixture"
IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE = "1"
FIXTURE_CONF
    bitbake -r "$fixture_conf" "${IMAGE}"
elif [[ "${IOTBENCH_ENABLE_REST_FIXTURE:-0}" == 1 ]]; then
    [[ "$FIRMWARE" == *-cwe022-rest-internal-files &&
       "${IOTBENCH_BUILD_MODE:-fixture}" == fixture &&
       "${IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_SUDO_ENV_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_TELNET_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_FTP_WRITE_FIXTURE:-0}" != 1 ]] || {
        echo "REST opt-in requires its own image, fixture mode and no other fixture opt-ins" >&2
        exit 1
    }
    fixture_conf=$(mktemp /tmp/iotbench-rest.XXXXXX.conf)
    trap 'rm -f "$fixture_conf"' EXIT
    cat > "$fixture_conf" <<'FIXTURE_CONF'
IOTBENCH_BUILD_MODE = "fixture"
IOTBENCH_ENABLE_REST_FIXTURE = "1"
FIXTURE_CONF
    bitbake -r "$fixture_conf" "${IMAGE}"
elif [[ "${IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE:-0}" == 1 ]]; then
    [[ "$FIRMWARE" == *-cwe798-password-leak-* &&
       "${IOTBENCH_BUILD_MODE:-fixture}" == fixture &&
       "${IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_SUDO_ENV_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_TELNET_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_FTP_WRITE_FIXTURE:-0}" != 1 ]] || {
        echo "Password Leak opt-in requires its own image, fixture mode and no other fixture opt-ins" >&2
        exit 1
    }
    fixture_conf=$(mktemp /tmp/iotbench-password-leak.XXXXXX.conf)
    trap 'rm -f "$fixture_conf"' EXIT
    cat > "$fixture_conf" <<'FIXTURE_CONF'
IOTBENCH_BUILD_MODE = "fixture"
IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE = "1"
FIXTURE_CONF
    bitbake -r "$fixture_conf" "${IMAGE}"
elif [[ "${IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE:-0}" == 1 ]]; then
    [[ "$FIRMWARE" == *-cwe088-cronjob-wildcard-injection &&
       "${IOTBENCH_BUILD_MODE:-fixture}" == fixture &&
       "${IOTBENCH_ENABLE_SUDO_ENV_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_TELNET_FIXTURE:-0}" != 1 &&
       "${IOTBENCH_ENABLE_FTP_WRITE_FIXTURE:-0}" != 1 ]] || {
        echo "Cron wildcard opt-in requires its own image, fixture build mode and no other fixture opt-ins" >&2
        exit 1
    }
    fixture_conf=$(mktemp /tmp/iotbench-cron-wildcard.XXXXXX.conf)
    trap 'rm -f "$fixture_conf"' EXIT
    cat > "$fixture_conf" <<'FIXTURE_CONF'
IOTBENCH_BUILD_MODE = "fixture"
IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE = "1"
FIXTURE_CONF
    bitbake -r "$fixture_conf" "${IMAGE}"
else
    bitbake "${IMAGE}"
fi

DEPLOY_DIR="${BUILDDIR}/tmp/deploy/images/${MACHINE}"
KERNEL=$(sed -n 's/^kernel_imagetype = //p' "${DEPLOY_DIR}/${IMAGE}-${MACHINE}.rootfs.qemuboot.conf")

EXPORT_DIR="/export/${FIRMWARE}/${MACHINE}"
mkdir -p "${EXPORT_DIR}"
cp -L "${DEPLOY_DIR}/${IMAGE}-${MACHINE}.rootfs.ext4.zst" "${DEPLOY_DIR}/${KERNEL}" "${EXPORT_DIR}/"
echo "Firmware exported to deploy-images/${FIRMWARE}/${MACHINE}"
