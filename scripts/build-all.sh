#!/bin/sh
# Build the firmware catalog.
#
# By default this builds the firmware that needs no opt-in flag, on one machine
# (qemuarm64), and builds an opt-in fixture family only when its
# IOTBENCH_ENABLE_*_FIXTURE flag is exported as 1. With --all it builds every
# firmware, opt-in fixtures included, on every QEMU machine unless a machine
# list is given. In both modes each firmware gets only the one opt-in flag it
# needs, because container-build-and-export.sh refuses to mix fixture families
# in a single build, so exporting every flag at once would make every build fail.
#
# Usage: scripts/build-all.sh [options]
#   -a, --all              build every opt-in fixture too, on every machine
#   -m, --machines LIST    QEMU machines to build (default: qemuarm64, or all
#                          five with --all)
#   -d, --devices LIST     only these device classes, e.g. "router plc"
#   -s, --scenarios LIST   only scenarios matching these globs,
#                          e.g. "cwe120-* cwe798-password-leak-*"
#   -f, --firmware LIST    only these exact firmware ids
#   -n, --dry-run          print the build commands without running them
#   -x, --fixed            also build the corrected twins (firmware ids ending in
#                          -fixed), whose weakness is removed
#       --only-fixed       build only the corrected twins
#   -l, --list             print "<firmware> <opt-in flag or ->" and exit
#   -k, --keep-going       continue after a failed build and report at the end
#   -r, --skip-existing    skip a build whose exported rootfs already exists
#       --build-builder    run "docker compose build yocto" before building
#   -h, --help             show this help
#
# Every option can also be given as an environment variable with the upper
# case name (MACHINES, DEVICES, SCENARIOS, FIRMWARES, DRY_RUN, KEEP_GOING,
# SKIP_EXISTING, BUILD_ALL, BUILD_BUILDER, BUILD_FIXED, ONLY_FIXED). Failed builds are written to
# FAILURES_FILE (default deploy-images/build-all-failures.txt).
#
# The optional IOTBENCH_NATIVE_BUFFER_ASAN and IOTBENCH_NATIVE_PATH_ASAN
# variables (0 or 1) are forwarded to the builds that read them.
set -eu

cd "$(dirname -- "$0")/.."

ALL_MACHINES="qemuarm64 qemuarm qemux86-64 qemux86 qemumips"
# Every opt-in flag this script knows how to set. A flag found in the recipes
# but missing here is reported, so new fixture families cannot be skipped
# silently.
KNOWN_FLAGS="IOTBENCH_ENABLE_APACHE_FIXTURE IOTBENCH_ENABLE_CONNECTION_FIXTURE
IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE IOTBENCH_ENABLE_CWE120_FIXTURE
IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE IOTBENCH_ENABLE_FTP_WRITE_FIXTURE
IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE
IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE
IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE
IOTBENCH_ENABLE_REST_FIXTURE IOTBENCH_ENABLE_SUDO_ENV_FIXTURE
IOTBENCH_ENABLE_TELNET_FIXTURE"
# The list above wraps lines, so collapse it to single spaces before the
# word-boundary matches below.
KNOWN_FLAGS=$(printf '%s' "$KNOWN_FLAGS" | tr '\n' ' ')

MACHINES="${MACHINES:-}"
DEVICES="${DEVICES:-}"
SCENARIOS="${SCENARIOS:-}"
FIRMWARES="${FIRMWARES:-}"
DRY_RUN="${DRY_RUN:-0}"
KEEP_GOING="${KEEP_GOING:-0}"
SKIP_EXISTING="${SKIP_EXISTING:-0}"
BUILD_ALL="${BUILD_ALL:-0}"
BUILD_BUILDER="${BUILD_BUILDER:-0}"
BUILD_FIXED="${BUILD_FIXED:-0}"
ONLY_FIXED="${ONLY_FIXED:-0}"
FAILURES_FILE="${FAILURES_FILE:-deploy-images/build-all-failures.txt}"
LIST_ONLY=0

die() {
    printf 'build-all: %s\n' "$*" >&2
    exit 2
}

usage() {
    sed -n '2,/^set -eu$/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
    case "$1" in
        -m|--machines|-d|--devices|-s|--scenarios|-f|--firmware)
            [ $# -ge 2 ] || die "$1 needs a value"
            case "$1" in
                -m|--machines) MACHINES=$2 ;;
                -d|--devices) DEVICES=$2 ;;
                -s|--scenarios) SCENARIOS=$2 ;;
                -f|--firmware) FIRMWARES=$2 ;;
            esac
            shift 2
            ;;
        -n|--dry-run) DRY_RUN=1; shift ;;
        -l|--list) LIST_ONLY=1; shift ;;
        -k|--keep-going) KEEP_GOING=1; shift ;;
        -r|--skip-existing) SKIP_EXISTING=1; shift ;;
        -a|--all) BUILD_ALL=1; shift ;;
        -x|--fixed) BUILD_FIXED=1; shift ;;
        --only-fixed) ONLY_FIXED=1; BUILD_FIXED=1; shift ;;
        --build-builder) BUILD_BUILDER=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown option: $1 (see --help)" ;;
    esac
done

if [ -z "$MACHINES" ]; then
    if [ "$BUILD_ALL" = 1 ]; then
        MACHINES=$ALL_MACHINES
    else
        MACHINES=qemuarm64
    fi
fi

# The opt-in flag a firmware needs, or nothing for the default build. These
# patterns mirror container-build-and-export.sh, plus the CWE-120 fixture whose
# guard lives in the vulnerability recipe instead of the image recipe.
fixture_flag_for() {
    # A corrected twin needs the same flag as the vulnerable image it mirrors.
    case "${1%-fixed}" in
        *-cwe276-bad-write-rights) echo IOTBENCH_ENABLE_FTP_WRITE_FIXTURE ;;
        *-cwe798-unencrypted-traffic) echo IOTBENCH_ENABLE_TELNET_FIXTURE ;;
        *-cwe798-sudo-environment) echo IOTBENCH_ENABLE_SUDO_ENV_FIXTURE ;;
        *-cwe088-cronjob-wildcard-injection) echo IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE ;;
        *-cwe798-password-leak-*) echo IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE ;;
        *-cwe022-rest-internal-files) echo IOTBENCH_ENABLE_REST_FIXTURE ;;
        *-cwe???-apache-web) echo IOTBENCH_ENABLE_APACHE_FIXTURE ;;
        *-cwe022-native-path-traversal|*-cwe020-native-filename-validation)
            echo IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE ;;
        *-cwe787-native-buffer-overflow) echo IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE ;;
        *-cwe020-native-connection-string) echo IOTBENCH_ENABLE_CONNECTION_FIXTURE ;;
        *-cwe061-native-symlink-following) echo IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE ;;
        *-cwe078-java-os-command-injection|*-cwe077-java-app-command-injection)
            echo IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE ;;
        *-cwe502-java-deserialization) echo IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE ;;
        *-cwe798-embedded-auth-*) echo IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE ;;
        *-cwe120-service-buffer-overflow) echo IOTBENCH_ENABLE_CWE120_FIXTURE ;;
        *) echo "" ;;
    esac
}

# True when $1 matches one of the remaining arguments used as case patterns.
matches_any() {
    value=$1
    shift
    for pattern in "$@"; do
        # The patterns are user globs, so they must stay unquoted.
        # shellcheck disable=SC2254
        case "$value" in
            $pattern) return 0 ;;
        esac
    done
    return 1
}

# Enumerate the recipes before disabling pathname expansion, which keeps the
# user supplied globs literal in the filters below.
FIRMWARE_LIST=$(
    for bb in meta-iotbench/recipes-images/iotbench-*.bb; do
        [ -e "$bb" ] || continue
        name=${bb##*/}
        name=${name%.bb}
        printf '%s\n' "${name#iotbench-}"
    done
)
[ -n "$FIRMWARE_LIST" ] || die "no firmware recipes found in meta-iotbench/recipes-images"
set -f

for machine in $MACHINES; do
    case " $ALL_MACHINES " in
        *" $machine "*) ;;
        *) die "unsupported machine: $machine (supported: $ALL_MACHINES)" ;;
    esac
done

# Report opt-in flags present in the recipes that this script does not know.
UNKNOWN=$(
    grep -rhoE 'IOTBENCH_ENABLE_[A-Z0-9_]+_FIXTURE' meta-iotbench 2>/dev/null | sort -u |
    while IFS= read -r flag; do
        case " $KNOWN_FLAGS " in
            *" $flag "*) ;;
            *) printf '%s ' "$flag" ;;
        esac
    done
)
if [ -n "$UNKNOWN" ]; then
    printf 'WARNING: unknown opt-in flags in the recipes, add them to KNOWN_FLAGS and fixture_flag_for: %s\n' \
        "$UNKNOWN" >&2
fi

# Select the firmware ids that pass the filters.
SELECTED=$(
    # The filter lists are split on purpose, and set -f keeps their globs literal.
    # shellcheck disable=SC2086
    printf '%s\n' "$FIRMWARE_LIST" | while IFS= read -r firmware; do
        device=${firmware%%-*}
        scenario=${firmware#*-}
        case "$firmware" in
            *-fixed) [ "$BUILD_FIXED" = 1 ] || continue ;;
            *) [ "$ONLY_FIXED" != 1 ] || continue ;;
        esac
        if [ -n "$FIRMWARES" ] && ! matches_any "$firmware" $FIRMWARES; then continue; fi
        if [ -n "$DEVICES" ] && ! matches_any "$device" $DEVICES; then continue; fi
        if [ -n "$SCENARIOS" ] && ! matches_any "$scenario" $SCENARIOS; then continue; fi
        printf '%s\n' "$firmware"
    done
)
[ -n "$SELECTED" ] || die "the filters select no firmware"
COUNT=$(printf '%s\n' "$SELECTED" | wc -l | tr -d ' ')

if [ "$LIST_ONLY" = 1 ]; then
    printf '%s\n' "$SELECTED" | while IFS= read -r firmware; do
        flag=$(fixture_flag_for "$firmware")
        printf '%s %s\n' "$firmware" "${flag:--}"
    done
    OPT_IN=$(printf '%s\n' "$SELECTED" | while IFS= read -r firmware; do
        [ -n "$(fixture_flag_for "$firmware")" ] && echo x
    done | wc -l | tr -d ' ')
    printf '%s firmware recipes, %s need an opt-in flag, %s build by default\n' \
        "$COUNT" "$OPT_IN" "$((COUNT - OPT_IN))" >&2
    exit 0
fi

# Run, or print, one build. Arguments are the machine, the firmware id and the
# opt-in flag (possibly empty).
build_one() {
    machine=$1
    firmware=$2
    flag=$3
    # Compose maps IOTBENCH_ENABLE_CWE120_FIXTURE from the environment into the
    # container, so it is an environment variable here and not a docker
    # argument, which keeps an ordinary build identical to a plain
    # "docker compose run --rm yocto". It is always set, to 1 for the CWE-120
    # family and to 0 otherwise, so a value exported in the calling shell cannot
    # leak into a build of a different family.
    cwe120=0
    set --
    case "$flag" in
        "") ;;
        IOTBENCH_ENABLE_CWE120_FIXTURE) cwe120=1 ;;
        *) set -- -e "$flag=1" -e "IOTBENCH_BUILD_MODE=${IOTBENCH_BUILD_MODE:-fixture}" ;;
    esac
    case "$flag" in
        IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE)
            if [ -n "${IOTBENCH_NATIVE_BUFFER_ASAN-}" ]; then
                set -- "$@" -e "IOTBENCH_NATIVE_BUFFER_ASAN=$IOTBENCH_NATIVE_BUFFER_ASAN"
            fi ;;
        IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE)
            if [ -n "${IOTBENCH_NATIVE_PATH_ASAN-}" ]; then
                set -- "$@" -e "IOTBENCH_NATIVE_PATH_ASAN=$IOTBENCH_NATIVE_PATH_ASAN"
            fi ;;
    esac
    if [ "$DRY_RUN" = 1 ]; then
        printf 'YOCTO_MACHINE=%s FIRMWARE=%s IOTBENCH_ENABLE_CWE120_FIXTURE=%s docker compose run --rm%s yocto\n' \
            "$machine" "$firmware" "$cwe120" "${*:+ $*}"
        return 0
    fi
    YOCTO_MACHINE="$machine" FIRMWARE="$firmware" IOTBENCH_ENABLE_CWE120_FIXTURE="$cwe120" \
        docker compose run --rm "$@" yocto
}

if [ "$DRY_RUN" != 1 ]; then
    command -v docker >/dev/null 2>&1 || die "docker is required (use --dry-run to only print the commands)"
    if [ "$BUILD_BUILDER" = 1 ]; then
        docker compose build yocto
    fi
fi

# shellcheck disable=SC2086
MACHINE_COUNT=$(printf '%s\n' $MACHINES | wc -l | tr -d ' ')
TOTAL=$((COUNT * MACHINE_COUNT))
BUILT=0
SKIPPED=0
FAILED=0
INDEX=0
FAILED_LIST=""

for machine in $MACHINES; do
    while IFS= read -r firmware; do
        INDEX=$((INDEX + 1))
        flag=$(fixture_flag_for "$firmware")
        if [ "$BUILD_ALL" != 1 ] && [ -n "$flag" ]; then
            # The flag names come from the fixed table above, so eval is safe.
            enabled=0
            eval "enabled=\${$flag-0}"
            if [ "$enabled" != 1 ]; then
                SKIPPED=$((SKIPPED + 1))
                [ "$DRY_RUN" = 1 ] || echo "Skipping opt-in fixture ${firmware} (set ${flag}=1 to include)"
                continue
            fi
        fi
        rootfs="deploy-images/${firmware}/${machine}/iotbench-${firmware}-${machine}.rootfs.ext4.zst"
        if [ "$SKIP_EXISTING" = 1 ] && [ -f "$rootfs" ]; then
            SKIPPED=$((SKIPPED + 1))
            [ "$DRY_RUN" = 1 ] || echo "[$INDEX/$TOTAL] skip ${firmware} (${machine}), already exported"
            continue
        fi
        [ "$DRY_RUN" = 1 ] || echo "[$INDEX/$TOTAL] ${firmware} (${machine}) ${flag:+opt-in $flag}"
        if build_one "$machine" "$firmware" "$flag"; then
            BUILT=$((BUILT + 1))
        else
            FAILED=$((FAILED + 1))
            FAILED_LIST="${FAILED_LIST}${machine} ${firmware}
"
            echo "FAILED: ${firmware} (${machine})" >&2
            if [ "$KEEP_GOING" != 1 ]; then
                echo "Stopping at the first failure, use --keep-going to continue." >&2
                exit 1
            fi
        fi
    done <<EOF
$SELECTED
EOF
done

if [ "$DRY_RUN" = 1 ]; then
    printf '# %s builds planned (%s firmware x %s machines)\n' "$TOTAL" "$COUNT" "$MACHINE_COUNT" >&2
    exit 0
fi

printf 'Summary: planned=%s built=%s skipped=%s failed=%s\n' "$TOTAL" "$BUILT" "$SKIPPED" "$FAILED"
if [ "$FAILED" -gt 0 ]; then
    mkdir -p "$(dirname -- "$FAILURES_FILE")"
    printf '%s' "$FAILED_LIST" > "$FAILURES_FILE"
    echo "Failed builds listed in $FAILURES_FILE" >&2
    exit 1
fi
echo "Catalog built. See deploy-images/<firmware>/<machine>/."
