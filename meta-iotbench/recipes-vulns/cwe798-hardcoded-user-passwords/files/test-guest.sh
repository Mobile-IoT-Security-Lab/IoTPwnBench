#!/bin/sh
# Explicitly invoked local guest regression; changes are restored on exit.
set -eu
accounts='@SYSCONFDIR@/iotbench/hardcoded-user-passwords/accounts.conf'
helper='@BINDIR@/iotbench-fixture-auth'
device=${1:?Expected synthetic device class}
grep -Fx "DEVICE_CLASS=\"$device\"" '@SYSCONFDIR@/iotbench/device.conf' >/dev/null
[ "$(cat "$accounts")" = 'fixtureuser:fixture-password-123' ]
[ "$(stat -c '%u:%g:%a' "$accounts")" = '0:0:600' ]
[ "$(stat -c '%u:%g:%a' "$helper")" = '0:0:755' ]
printf '%s\n' 'PASS deterministic synthetic account, device identity and normal permissions'

check_auth() {
    expected_exit=$1
    account=$2
    password=$3
    actual_exit=0
    output=$(printf '%s\n' "$password" | "$helper" "$account") || actual_exit=$?
    [ "$actual_exit" -eq "$expected_exit" ]
    if [ "$expected_exit" -eq 0 ]; then
        printf '%s\n' "$output" | grep -Fx 'HARDCODED_USER_PASSWORD_ACCEPTED' >/dev/null
        printf '%s\n' "$output" | grep -Fx 'AUTHENTICATED_AS=fixtureuser' >/dev/null
    else
        if printf '%s\n' "$output" | grep -F 'HARDCODED_USER_PASSWORD_ACCEPTED' >/dev/null; then
            exit 1
        fi
    fi
}

check_auth 0 fixtureuser fixture-password-123
check_auth 0 fixtureuser fixture-password-123
check_auth 1 fixtureuser fixture-password-wrong
check_auth 1 fixtureother fixture-password-123
check_auth 1 fixtureuser ''
check_auth 1 '' fixture-password-123
check_auth 1 fixtureuser '$(printf injected); ../fixture-only'
actual_exit=0
output=$("$helper" fixtureuser < /dev/null) || actual_exit=$?
[ "$actual_exit" -eq 1 ]
actual_exit=0
output=$(printf '%s\n' fixture-password-123 | "$helper" fixtureuser extra) || actual_exit=$?
[ "$actual_exit" -eq 2 ]
printf '%s\n' 'PASS repeated correct credential; wrong, empty, missing and malformed input rejected'

# Demonstrate the link from the installed account record to authentication.
# This is test-harness code, not installation-time credential provisioning.
temporary=$(mktemp -d)
cp "$accounts" "$temporary/accounts.conf"
trap 'cp "$temporary/accounts.conf" "$accounts"; chmod 0600 "$accounts"; rm -rf "$temporary"' EXIT
printf '%s\n' 'fixtureuser:fixture-password-rotated-test-only' > "$accounts"
check_auth 1 fixtureuser fixture-password-123
check_auth 0 fixtureuser fixture-password-rotated-test-only
printf '%s\n' 'PASS authentication consumes the installed account password'

printf '%s\n' 'fixtureuser:' > "$accounts"
check_auth 2 fixtureuser ''
rm "$accounts"
check_auth 2 fixtureuser fixture-password-123
cp "$temporary/accounts.conf" "$accounts"
chmod 0600 "$accounts"
check_auth 0 fixtureuser fixture-password-123
printf '%s\n' 'PASS missing or empty credential store fails closed; original credential restored'
