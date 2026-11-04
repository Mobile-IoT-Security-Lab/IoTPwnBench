#!/bin/sh
# Start the installed Apache CGI fixture for a researcher-driven terminal test.
# This stages only fixed package files, then reuses the existing namespace
# launcher. It sends no HTTP request and performs no assertion.
set -eu

BASE=/usr/share/iotbench/apache-fixture
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH

usage() {
    echo "usage: $0 --isolated-fixture" >&2
    exit 2
}

fail() {
    echo "Apache fixture launcher: $*" >&2
    exit 1
}

[ "${1:-}" = "--isolated-fixture" ] && [ "$#" -eq 1 ] || usage
[ "$(id -u)" -ne 0 ] || fail "run as the unprivileged iotapache account"
[ -x "$BASE/isolate" ] || fail "missing installed namespace launcher"
[ -f "$BASE/scenario.py" ] || fail "missing selected scenario"

HTTPD=/usr/sbin/httpd
[ -x "$HTTPD" ] || fail "missing Apache httpd"
SQLITE=$(command -v sqlite3 || true)
[ -n "$SQLITE" ] || fail "missing sqlite3 client"
command -v curl >/dev/null 2>&1 || fail "missing curl client"
command -v ldd >/dev/null 2>&1 || fail "missing ldd"

MODULE_DIR=
for candidate in /usr/lib/apache2/modules /usr/libexec/apache2/modules; do
    if [ -d "$candidate" ]; then
        MODULE_DIR=$candidate
        break
    fi
done
[ -n "$MODULE_DIR" ] || fail "missing Apache module directory"

ROOT=$(mktemp -d /tmp/iotbench-apache-manual.XXXXXX) || fail "cannot create private staging directory"
cleanup() {
    rm -rf "$ROOT"
}
trap cleanup EXIT HUP INT TERM
umask 077

copy_path() {
    source_path=$1
    destination=$2
    [ -e "$source_path" ] || fail "missing runtime path $source_path"
    mkdir -p "$ROOT$(dirname "$destination")"
    cp -R "$source_path" "$ROOT$destination"
}

copy_dependencies() {
    source_path=$1
    if ldd "$source_path" 2>/dev/null | grep -q 'not found'; then
        fail "missing shared library for $source_path"
    fi
    ldd "$source_path" 2>/dev/null | awk '{
        for (i = 1; i <= NF; i++) {
            if ($i ~ /^\//) {
                print $i
                break
            }
        }
    }' | while IFS= read -r library; do
        [ -n "$library" ] || continue
        resolved=$(readlink -f "$library") || exit 1
        copy_path "$resolved" "$library"
    done
}

copy_binary() {
    source_path=$(readlink -f "$1") || fail "cannot resolve $1"
    destination=$2
    copy_path "$source_path" "$destination"
    copy_dependencies "$source_path"
}

mkdir -p "$ROOT"/oldroot "$ROOT"/proc "$ROOT"/state "$ROOT"/tmp "$ROOT"/run \
    "$ROOT"/dev/shm "$ROOT"/fixture "$ROOT"/modules "$ROOT"/empty "$ROOT"/attacker "$ROOT"/etc
for device in null zero random urandom; do
    : > "$ROOT/dev/$device"
done
printf 'fixture:x:1000:1000:Synthetic fixture:/tmp:/bin/sh\n' > "$ROOT/etc/passwd"
printf 'fixture:x:1000:\n' > "$ROOT/etc/group"
printf 'passwd: files\ngroup: files\nhosts: files\n' > "$ROOT/etc/nsswitch.conf"
printf '127.0.0.1 localhost\n' > "$ROOT/etc/hosts"

copy_binary "$HTTPD" /usr/sbin/httpd
copy_binary /usr/bin/python3 /usr/bin/python3
copy_binary /bin/sh /bin/sh
copy_binary "$SQLITE" /usr/bin/sqlite3
for utility in id cat rm mkdir sed; do
    utility_path=$(command -v "$utility") || fail "missing required utility $utility"
    copy_binary "$utility_path" "$utility_path"
done

PYTHON_STDLIB=
for candidate in /usr/lib/python3.*; do
    if [ -d "$candidate" ]; then
        PYTHON_STDLIB=$candidate
        break
    fi
done
[ -n "$PYTHON_STDLIB" ] || fail "missing Python standard library"
mkdir -p "$ROOT/usr/lib"
cp -R "$PYTHON_STDLIB" "$ROOT/usr/lib/"
find "$PYTHON_STDLIB" -type f -name '*.so' -print | while IFS= read -r extension; do
    copy_binary "$extension" "$extension"
done
find /lib /usr/lib -type f -name libnss_files.so.2 -print 2>/dev/null | while IFS= read -r nss; do
    copy_binary "$nss" "$nss"
done

cp "$BASE/app.cgi" "$BASE/manual-server.sh" "$BASE/scenario.py" "$BASE/variant.json" \
    "$ROOT/fixture/"
cp "$BASE/httpd.conf.in" "$ROOT/fixture/httpd.conf"
chmod 0755 "$ROOT/fixture/app.cgi" "$ROOT/fixture/manual-server.sh"
for module in mpm_prefork authz_core unixd alias cgi; do
    if "$HTTPD" -l | grep -Fq "mod_${module}.c"; then
        sed "/^LoadModule ${module}_module /d" "$ROOT/fixture/httpd.conf" > "$ROOT/fixture/httpd.conf.next"
        mv "$ROOT/fixture/httpd.conf.next" "$ROOT/fixture/httpd.conf"
    else
        copy_binary "$MODULE_DIR/mod_${module}.so" "/modules/mod_${module}.so"
    fi
done

"$BASE/isolate" --isolated-fixture "$ROOT" /fixture/manual-server.sh &
isolate_pid=$!
printf 'manual-launch-pid=%s\n' "$isolate_pid" >&2
wait "$isolate_pid"
