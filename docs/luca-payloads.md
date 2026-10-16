# Luca Payloads

This guide documents the Luca firmware scenarios and their reproducible lab
payloads. See [Hardcoded credentials (CWE-798)](#hardcoded-credentials-cwe-798)
for the shared vendor support account on all eleven devices. The separate
[Hardcoding User Passwords](#hardcoded-credentials--hardcoding-user-passwords-cwe-798)
fixtures model a fixed synthetic account password through local authentication.
The [Vulnerable Bash Files — Path Traversal](#vulnerable-bash-files--path-traversal-cwe-22)
fixtures model unvalidated local path concatenation in a firmware Bash helper.

The [Vulnerable C Binaries — SQL injection](#vulnerable-c-binaries--sql-injection-cwe-89)
fixtures model native C argument interpolation into a local SQLite SELECT.

The [Vulnerable C Binaries — Null Pointer Dereference](#vulnerable-c-binaries--null-pointer-dereference-cwe-476)
fixtures model an input-dependent record lookup returning a pointer that is
subsequently dereferenced without NULL validation.

The [Vulnerable C Binaries — Integer Overflow](#vulnerable-c-binaries--integer-overflow-cwe-190)
fixtures model validated numeric input reaching unchecked uint32_t multiplication
and a synthetic capacity decision that uses the wrapped result.

The [Vulnerable Java JARs — SQL Injection](java-sql-injection.md) fixtures
model Java bytecode concatenating a local record name into a read-only SQLite
JDBC SELECT, with one firmware for every existing device. That guide records
the dependencies, exact flow, payloads, build/test commands and validation.

## Weak Cipher: 3DES Device Backups

These images implement intentionally vulnerable device backup encryption under
[CWE-327](https://cwe.mitre.org/data/definitions/327.html) (use of a broken or
risky cryptographic algorithm). The package directory is
`meta-iotbench/recipes-vulns/weak-cipher/`; its BitBake package is `cwe327-weak-cipher`.
The image IDs follow `<device>-cwe327-weak-cipher` for all eleven device profiles
listed in the root README. The recipes work with the existing architecture
selector and require no new layers or external source downloads.

### Scenario and scope

The shared web admin encrypts and restores device backup text using three-key
Triple DES in CBC mode with PKCS#7 padding. OpenSSL's
[`EVP_des_ede3_cbc()`](https://docs.openssl.org/3.0/man3/EVP_des_cbc/)
performs the actual encryption. The helper links against `libcrypto`; it does
not depend on PHP's optional OpenSSL extension, which the platform disables.

Triple DES has a 64-bit block size and is an obsolete choice for new encrypted
data; [NIST withdrew its TDEA recommendation in January 2024](https://www.nist.gov/news-events/news/2023/06/nist-withdraw-special-publication-800-67-revision-2).
The scenario also intentionally embeds publicly known keys and reuses a fixed IV.
Anyone with these constants can decrypt backups and generate valid frames.
Each image installs only this vulnerability package, retains its
device profile and exposes the scenario through HTTP on the shared dashboard.
The native MQTT, camera and Modbus services keep their normal telemetry role;
the encrypted backup interface is the same for all devices.

The helper contains the following hardcoded constants, identical in all eleven
device images (hexadecimal bytes, not ASCII strings):

| Constant | Bytes | Hex value |
| --- | --- | --- |
| 3DES key | 24 | `0123456789abcdef23456789abcdef01456789abcdef0123` |
| CBC IV | 8 | `1234567890abcdef` |
| HMAC-SHA256 key | 32 | `a0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebf` |

These values are compiled into `iotbench-weak-cipher`; no random keys, random
IVs, runtime key files or per-device overrides are used. Identical plaintext
produces identical ciphertext and tags across requests, reboots, fresh QEMU
snapshots and different device profiles. Backups can be restored across these
images. Backups made by the previous random-key implementation are incompatible.

The existing frame format retains HMAC-SHA256 over the IV and ciphertext.
Malformed frames and modifications without a recomputed tag are rejected before
decryption. Since the HMAC key is also public, this check provides no trustworthy
authentication: anyone can recompute a valid tag. Frames must carry the fixed IV.

### Build and boot

From the repository root:

```bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe327-weak-cipher'
FIRMWARE=router-cwe327-weak-cipher docker compose run --rm yocto
FIRMWARE=router-cwe327-weak-cipher ./scripts/run-qemu.sh
```

Replace `router` with any supported device. The root README provides the loop
to build all eleven images. Output is exported to
`deploy-images/<device>-cwe327-weak-cipher/<machine>/`.

### Dashboard and HTTP API

Open `http://127.0.0.1:8080`, locate **Device Backup Encryption**, leave the
operation as **Encrypt**, and submit backup text. The output begins with:

```text
cipher=3DES-CBC
block_bits=64
3DES-CBC:<hexadecimal-frame>
```

Copy only the `3DES-CBC:...` line into the text field, select **Decrypt**, and
submit again. The original backup text is returned. Encrypting the same input
twice gives the same frame because both key and IV are fixed. Altering a hex digit in
a frame returns `Invalid encrypted frame`.

For direct API use, load `/`, read `meta[name="dashboard-token"]`, and send
JSON to `/api.php` with `X-Dashboard-Token: <token>`:

```json
{"action":"weak_cipher","operation":"encrypt","data":"{\"backup\":\"device-settings\"}"}
```

The response contains `ok`, `cipher`, `block_bits`, `result`, and the display
`output`. Submit the encryption response's `result` as `data` with
`"operation":"decrypt"` to recover the plaintext. CSRF and HTTP method checks
are supplied by the shared dashboard. Backup text must be UTF-8 and no more
than 4096 bytes; the encrypted frame is at most 8297 ASCII characters. The CLI
also supports binary plaintext and empty input.

### Guest CLI and frame format

From the guest serial console:

```bash
printf '%s' 'device-backup' | iotbench-weak-cipher encrypt > /tmp/device-backup.enc
iotbench-weak-cipher decrypt < /tmp/device-backup.enc
```

The ciphertext is `3DES-CBC:` followed by hex-encoded
`IV[8] || ciphertext[multiple of 8] || HMAC-SHA256[32]`. The CLI emits a
newline after the frame; decryption accepts that newline and emits the exact
plaintext bytes. The same embedded constants are used by the guest console and
the dashboard, which runs as `routerweb`.

The CLI accepts only `encrypt` or `decrypt`; there is no key-file argument.
The web action passes input through stdin and invokes a fixed argument vector
without a shell.

### Verification

The regression script exercises binary/text round trips, the 4096-byte limit,
hardcoded key/IV interoperability with OpenSSL, identical output from separate
processes, frame creation using the published keys, malformed input rejection and absence of
runtime key files. It requires Python 3, the compiled helper and the
OpenSSL CLI on the test host:

```bash
python3 scripts/test-weak-cipher.py /path/to/iotbench-weak-cipher
```

For a host build, compile against the host OpenSSL headers/library (this is a
test binary, separate from the cross-compiled Yocto image):

```bash
cc -std=c11 -Wall -Wextra -Werror \
  meta-iotbench/recipes-vulns/weak-cipher/files/iotbench-weak-cipher.c \
  $(pkg-config --cflags --libs openssl) -o /tmp/iotbench-weak-cipher
python3 scripts/test-weak-cipher.py /tmp/iotbench-weak-cipher
```

For runtime validation, boot each exported image and perform the dashboard
round trip above, or run the HTTP regression client against the booted image:

```bash
python3 scripts/test-weak-cipher-http.py
# Optional URL when QEMU_HTTP_PORT differs from 8080:
python3 scripts/test-weak-cipher-http.py http://127.0.0.1:18080
```

The helper runs under the existing service sandbox. A
lighttpd drop-in permits writes only to `/var/lib/router-dashboard` for
dashboard state; it needs no privilege escalation or additional
service ports.

## Permitted Root SSH Login (CWE-276)

The `cwe276-permit-root-login` module intentionally permits direct SSH login
as `root` using a password. Image IDs follow
`<device>-cwe276-permit-root-login` for all eleven device profiles. Evaluate
the scenario through the effective SSH configuration, an actual login attempt
and the privileges obtained. Source inspection alone does not confirm that a
running firmware accepts the login; the commands below are a verification
procedure, not a record of completed runtime tests.

### Configuration and security implications

The module recipe is
[`cwe276-permit-root-login_1.0.bb`](../meta-iotbench/recipes-vulns/cwe276-permit-root-login/cwe276-permit-root-login_1.0.bb).
It depends on `openssh-sshd` and installs
[`00-iotbench-permit-root-login.conf`](../meta-iotbench/recipes-vulns/cwe276-permit-root-login/files/00-iotbench-permit-root-login.conf)
under `/etc/ssh/sshd_config.d/`, with these settings:

```text
PermitRootLogin yes
PasswordAuthentication yes
PermitEmptyPasswords no
```

This policy permits root password authentication but rejects empty passwords.
The lab credential documented in the [root README](../README.md#firmware-shell-access)
is username `root`, password `routeradmin`. The common
[`iotbench-image.inc`](../meta-iotbench/recipes-images/iotbench-image.inc)
sets the root password using a SHA-512 crypt hash shared across the images.
Storing a hash does not remove the risk of a publicly known default password.

The security risk combines a reachable SSH service, a known default credential
and immediate administrative access. The project labels the permissive default
policy as [CWE-276: Incorrect Default Permissions](https://cwe.mitre.org/data/definitions/276.html).
The presence of `PermitRootLogin yes` alone does not establish that an attacker
can authenticate: the effective configuration, account state and network
reachability must also be checked.

### Build and boot

From the repository root, build the image if it has not already been exported,
then boot it:

```bash
FIRMWARE=router-cwe276-permit-root-login docker compose run --rm yocto
FIRMWARE=router-cwe276-permit-root-login ./scripts/run-qemu.sh
```

Replace `router` with another supported device if needed. The existing
`YOCTO_MACHINE` selector applies to both build and boot. By default,
`run-qemu.sh` forwards host `127.0.0.1:2222` to guest TCP port 22 for these
images; `QEMU_SSH_PORT` changes the host port. Use a second host terminal for
the SSH test while QEMU remains running.

### Verify the effective configuration

Log in through the guest serial console as `root` with password `routeradmin`,
then run inside the guest:

```bash
/usr/sbin/sshd -t
/usr/sbin/sshd -T | grep -E \
  '^(permitrootlogin|passwordauthentication|permitemptypasswords|authenticationmethods) '
```

`sshd -t` should exit successfully. The effective configuration for the
intended scenario should contain at least:

```text
permitrootlogin yes
passwordauthentication yes
permitemptypasswords no
```

Also inspect `authenticationmethods` for any additional authentication
requirements. The installed fragment must be included by the main
`/etc/ssh/sshd_config`. OpenSSH normally uses the first value encountered for
a setting, and included wildcard files are processed in lexical order. A
fragment's contents alone therefore do not prove which policy applies.
See the [OpenSSH configuration manual](https://man.openbsd.org/sshd_config.5).

If the configuration contains `Match` blocks, use `sshd -T -C` with the actual
connection parameters, including `user=root` and the source address as seen
by the guest. If the running service uses a custom configuration file or
command-line overrides, reproduce those options in the verification command.
`sshd -T` evaluates configuration on disk; a real login also verifies the
behavior of the running service. See the
[OpenSSH test-mode documentation](https://man.openbsd.org/sshd.8).

### Verify login and privileges without changing the guest

From the second terminal on the host:

```bash
ssh -p 2222 \
  -o PreferredAuthentications=password \
  -o PubkeyAuthentication=no \
  -o NumberOfPasswordPrompts=1 \
  root@127.0.0.1 'id'
```

Enter `routeradmin` when prompted. These options select password authentication
and avoid accidentally demonstrating access through an existing SSH key.
Adjust `-p` if you set `QEMU_SSH_PORT`.

An output containing `uid=0(root)` confirms that the default password grants
remote command execution with root privileges. The `id` command provides
evidence without modifying files; no destructive operation is needed to
demonstrate the impact.

| Result | Interpretation |
| --- | --- |
| Connection refused or timeout | Investigate service availability, port forwarding or network reachability; authentication security has not yet been evaluated. |
| `Permission denied` | Authentication was rejected; check effective policy, credential and account state before drawing a conclusion. |
| Command output contains `uid=0(root)` | Direct root access with the default password is confirmed. |

### Exposure and severity

The provided QEMU forwarding binds to `127.0.0.1`, so that forwarded SSH port
is reachable from the local host. This limits exposure in the supplied lab
setup; it does not correct the guest's permissive authentication policy.
On a device reachable from a LAN or the Internet, anyone who knows the default
password could obtain root access if the same login behavior applies.

Such access can compromise the firmware's data, services and configuration.
Assess severity from actual reachability, whether the default credential is
still valid, any additional authentication requirements and the scope of the
obtained privileges. Record the tested image and architecture, effective
settings, connection endpoint and `id` output as evidence.

### Remediation and verification

For a firmware intended for real use, disable direct root SSH login:

```text
PermitRootLogin no
```

Provide access through individual accounts and grant administrative privileges
only where needed. Replace the shared default credential. If password
authentication is unnecessary, use key authentication for those accounts and
disable password authentication according to the deployment's access policy.

`PermitRootLogin prohibit-password` blocks root password and
keyboard-interactive authentication but still allows other methods, such as
public keys. It is not equivalent to disabling all root SSH login. See
[`PermitRootLogin` in the OpenSSH manual](https://man.openbsd.org/sshd_config.5#PermitRootLogin).

When applying a fix, remove or change the permissive setting in the effective
configuration; appending a later conflicting directive may not override it.
Validate with `sshd -t`, reload or restart the SSH service and repeat the
configuration and login checks. Keep serial access available while doing so.

The correction is demonstrated when SSH remains operational, the intended
non-root account can still authenticate, and direct root login is rejected
even with the correct password. For `PermitRootLogin no`, verify that root key
authentication is also rejected if a root key was previously authorized.
The default QEMU run discards guest changes when it exits, so a lasting fix
must be applied to the firmware sources and verified in a rebuilt image.

## Allow anonymous login (CWE-276)

### Scenario and CWE mapping

Each `<device>-cwe276-allow-anonymous-login` firmware enables anonymous FTP
access to a maintenance backup by default. The supported devices are `router`,
`ipcamera`, `smartplug`, `thermostat`, `plc`, `smartbulb`, `smarthub`, `envsensor`,
`smartspeaker`, `healthmonitor` and `doorlock`. These are separate images from
both the weak-cipher and permitted-root-login scenarios above; each installs
one vulnerability package and keeps its device profile, web admin, native
service and peripheral simulator.

The project maps this scenario to
[CWE-276: Incorrect Default Permissions](https://cwe.mitre.org/data/definitions/276.html).
The defect is a shipped maintenance-access policy that grants everyone read
access to settings intended for maintenance staff. Anonymous FTP can be
appropriate for intentionally public files; exposing a private configuration
backup under that policy is the weakness reproduced here. The benchmark uses
simulated data only.

The attacker needs network access to FTP and no account or prior foothold.
The expected impact is disclosure of device identity, network configuration
and peripheral layout. The anonymous session is read-only and confined to its
FTP directory. It does not provide a shell or administrative privileges.

### Package and runtime behavior

The package is
[`cwe276-allow-anonymous-login`](../meta-iotbench/recipes-vulns/cwe276-allow-anonymous-login/cwe276-allow-anonymous-login_1.0.bb).
It uses `vsftpd` from the already enabled, pinned `meta-networking` layer;
there is no change to the shared platform configuration or other firmware
variants. The upstream package creates the `ftp` account, enables
`vsftpd.service` and provides its empty privilege-separation directory.

A systemd drop-in replaces the service command with:

```text
/usr/sbin/vsftpd /etc/iotbench/vsftpd-anonymous.conf
```

The installed [configuration](../meta-iotbench/recipes-vulns/cwe276-allow-anonymous-login/files/vsftpd-anonymous.conf)
contains these key settings:

```text
anonymous_enable=YES
no_anon_password=YES
ftp_username=ftp
anon_root=/var/lib/ftp
anon_world_readable_only=YES
local_enable=NO
write_enable=NO
pasv_min_port=30000
pasv_max_port=30009
port_enable=NO
```

Both `anonymous` and `ftp` select anonymous access. `no_anon_password=YES`
permits login without a `PASS` command. See the
[upstream vsftpd configuration reference](https://security.appspot.com/vsftpd/vsftpd_conf.html)
for these options.

Before starting the daemon, the
[backup helper](../meta-iotbench/recipes-vulns/cwe276-allow-anonymous-login/files/iotbench-anonymous-backup)
copies the following files into `/var/lib/ftp/` and sets mode `0644`:

| Download | Original source | Contents |
| --- | --- | --- |
| `device.conf` | `/etc/iotbench/device.conf` | Device display name and class |
| `peripherals.conf` | `/etc/iotbench/peripherals.conf` | Device-specific sensor/actuator specification |
| `settings.json` | `/var/lib/router-dashboard/settings.json` | Shared web-admin network and Wi-Fi settings |
| `README.txt` | Installed by the vulnerability package | Scenario description |

The original dashboard settings are installed with mode `0640` in a `0750`
service directory. Publishing a world-readable copy inside the anonymous FTP
root deliberately removes that access boundary. The exported directory is
root-owned with mode `0755`, so the `ftp` user cannot write there. Uploads,
directory creation, deletion and local-account FTP logins are disabled.
The backup is a snapshot at FTP service startup; restart `vsftpd.service`
to refresh it after changing dashboard settings. The settings schema is shared
across devices, while identity and peripherals differ by device.

### Build and boot

From the repository root, validate recipes and dependencies, build and boot:

```bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe276-allow-anonymous-login'
FIRMWARE=router-cwe276-allow-anonymous-login docker compose run --rm yocto
QEMU_FTP_PORT=22121 FIRMWARE=router-cwe276-allow-anonymous-login ./scripts/run-qemu.sh
```

Replace `router` with any device listed above. To build all eleven images:

```bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe276-allow-anonymous-login.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
```

The default machine is `qemuarm64`. Set `YOCTO_MACHINE` for another architecture
supported by the [root README](../README.md#architectures) at both build and
boot time. Outputs are the compressed ext4 root filesystem and kernel under
`deploy-images/<device>-cwe276-allow-anonymous-login/<machine>/`.

The examples in this section explicitly set `QEMU_FTP_PORT=22121`, so QEMU
forwards host `127.0.0.1:22121` to guest TCP port `21`. If `QEMU_FTP_PORT` is
unset, the script uses host port `2121` instead. Always use the host port
printed in the startup line `FTP: ftp://127.0.0.1:<port>` for curl and the
regression client. Changing the port requires restarting QEMU with the new
environment setting.

Passive data ports `30000-30009` are forwarded using the same host and guest
numbers. HTTP and the device's MQTT or Modbus forwarding remain available.
`QEMU_FTP_PORT` changes only the control port. To boot the PLC with the same
FTP endpoint used by the payloads below:

```bash
QEMU_FTP_PORT=22121 FIRMWARE=plc-cwe276-allow-anonymous-login ./scripts/run-qemu.sh
```

Use passive mode. EPSV clients use the control connection's address for data;
PASV clients must likewise use the host address instead of the guest's private
address. Modern curl defaults and the Python client below handle this. Forwarding
only port 21 is insufficient for listing or downloading. Keep `30000-30009`
free and run one anonymous-FTP QEMU instance at a time. All forwarding binds
only to loopback; on a directly reachable device the guest FTP listener would
be accessible at its own IP address.

### Payloads and expected results

Run these commands in a second host terminal while QEMU remains running with
`QEMU_FTP_PORT=22121`. List the directory and download the settings without a
real credential:

```bash
curl --fail --user 'anonymous:' --list-only ftp://127.0.0.1:22121/
curl --fail --user 'anonymous:' ftp://127.0.0.1:22121/settings.json
curl --fail --user 'anonymous:' ftp://127.0.0.1:22121/device.conf
```

Expected listing: `README.txt`, `device.conf`, `peripherals.conf`,
`settings.json`. The settings download returns JSON with fields such as
`lan_ip`, `ssid` and `dhcp_start`. The identity download identifies the selected
device class. Some clients still send an empty or placeholder `PASS`; it is
not checked as a credential in this scenario.

To show that login succeeds on `USER` alone:

```bash
python3 - <<'PY'
from ftplib import FTP
from io import BytesIO
with FTP() as ftp:
    ftp.connect('127.0.0.1', 22121, timeout=10)
    print(ftp.sendcmd('USER anonymous'))
    data = BytesIO()
    ftp.retrbinary('RETR settings.json', data.write)
    print(data.getvalue().decode())
    ftp.quit()
PY
```

Expected control response: `230 Login successful.` followed by the downloaded
settings. This establishes both credential-free login and actual data access.
A welcome banner or a successful TCP connection alone is insufficient evidence.

### Regression and guest inspection

The [regression client](../scripts/test-anonymous-login.py) uses Python's
standard library and tests both `anonymous` and the `ftp` alias. It verifies
login without `PASS`, passive listing, readable JSON settings, device identity,
peripheral download, rejection of upload/mkdir/delete, confinement of file
reads and rejection of root FTP login with the valid serial-console password.

```bash
python3 scripts/test-anonymous-login.py --device router --port 22121
# When the booted device is the PLC:
python3 scripts/test-anonymous-login.py --device plc --port 22121
```

Expected: three `PASS` lines and exit status zero. It works against any supported
architecture; test each exported device image separately.
If QEMU was started without a port override, use `2121` in the curl and inline
Python examples and pass `--port 2121` to the regression client (its default).

#### Connection refused: check the host control port

`curl: (7) Failed to connect to 127.0.0.1 port 2121` means curl could not
establish the TCP connection; it has not attempted FTP authentication. A QEMU
instance forwarding FTP on `22121` will not accept a connection on `2121`.
Use the endpoint printed by `run-qemu.sh`, keep QEMU running and wait for the
guest FTP service to start before running the payloads.

On macOS, inspect the listening ports:

```bash
lsof -nP -iTCP:2121 -iTCP:22121 -sTCP:LISTEN
```

If QEMU listens on `22121`, use the `22121` commands above. If neither port
is listening, start the selected firmware and check its startup output for
errors. A host forwarding failure, such as an occupied HTTP port, prevents QEMU
from starting; free the conflicting port or select another `QEMU_HTTP_PORT`.

#### Inspect the guest service

Log in on the guest serial console with the root credential from the README
and inspect the running service and exported files:

```bash
systemctl status vsftpd.service
systemctl cat vsftpd.service
cat /etc/iotbench/vsftpd-anonymous.conf
ls -ld /var/lib/router-dashboard /var/lib/ftp
ls -l /var/lib/router-dashboard/settings.json /var/lib/ftp/settings.json
```

Record the firmware ID, machine, service command, file permissions and FTP
client output. If control connects but transfers time out, check passive-port
forwarding. If login fails or the service is inactive, inspect
`journalctl -u vsftpd.service` and the installed drop-in. The upstream
`/etc/vsftpd.conf` is not the configuration used by this variant.

### Completed validation

On 2026-10-05, all eleven `qemuarm64` targets passed BitBake parsing,
dependency resolution and actual compilation/export. Each exported image was
booted in QEMU and passed the FTP regression client plus an HTTP dashboard
check. Router validation used TCG; the other ten used HVF with the host CPU.
The tested host control ports were FTP `22121` and HTTP `18080`, with passive
data on `30000-30009`.

Router serial inspection also confirmed an active `vsftpd.service`, the intended
configuration argument, a root-owned `0755` export directory and a `0644`
settings copy alongside the original `0640` file. The local artifact report,
including checksums, is `deploy-images/anonymous-login-qemuarm64-validation.txt`.
Other supported architectures have not been built or boot-tested for this
scenario in this validation run.

### Remediation and verification

Disable anonymous login in `/etc/iotbench/vsftpd-anonymous.conf`:

```text
anonymous_enable=NO
```

Remove maintenance backups from the public export and restrict their
permissions and directory access to the maintenance account. If remote backup
access is required, provide an authenticated maintenance service. Merely setting
`no_anon_password=NO` still allows anonymous login with an arbitrary password
and does not establish account authentication. Changing only the unused
upstream `/etc/vsftpd.conf` does not change this service's policy.

Restart the service and repeat the login/download checks. A corrected image
must reject `USER anonymous` / anonymous authentication before permitting any
backup download. The supplied regression client should fail against a fixed
image because its positive anonymous-access checks describe the vulnerable
benchmark. Apply lasting remediation in the sources and rebuild; default QEMU
snapshots discard guest edits on exit.

## Hardcoded credentials (CWE-798)

### Scenario, scope and attacker position

The firmware IDs are `<device>-cwe798-hardcoded-credentials` for all eleven
profiles in the root README. Each image combines its normal device profile
with the single vulnerability package `cwe798-hardcoded-credentials`.

The shared web admin exposes **Vendor Support Backup**, an authenticated
maintenance export. This implements the inbound variant of
[CWE-798: Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html):
input is checked against credentials embedded in the product, identical in
every installation, without a supported way to change them.

| Credential | Exact, case-sensitive value |
| --- | --- |
| Username | `support` |
| Password | `iotbench-support-2026` |

These are plaintext constants in
`/usr/share/router-dashboard/modules/hardcoded-credentials/module.php`.
There is no random provisioning, environment override, runtime password file
or password-change API. Knowing the credential from one extracted image gives
access to the same support function on every device and fresh boot.

The canonical attacker is a remote HTTP client with knowledge of the firmware
credential, acquired from firmware extraction or this published lab fixture.
The attacker loads the public dashboard to obtain its request token and submits
the credential to the support action. That token guards requests against CSRF;
it does not authenticate a support user.

The exported `backup.maintenance` object is read from a real installed file,
`/usr/share/iotbench/hardcoded-credentials/support-backup.json`, outside
`/www/pages`. It contains synthetic, maintenance-only provisioning and
inventory data; successful export also includes device identity, dashboard
settings and live peripheral values. The support credential guards this
maintenance export. The existing public dashboard/telemetry is still public;
this module does not add a login wall around the shared platform.

The support account is an application identity, not a Linux or SSH account.
The action runs as `routerweb`, with no sudo permission or shell execution.
Native camera, MQTT and Modbus services retain their normal telemetry role;
the HTTP support interface is the same across devices. There are no service
sandbox overrides or new layers. This scenario is separate from the router's
existing CWE-798 sudo/editor images.

For MQTT profiles, the shared Mosquitto build retains its systemd feature so
the upstream `Type=notify` unit finishes starting and releases the telemetry
publisher. TLS and websockets remain disabled in this lab build. The baseline
broker listens on guest loopback; inspect native telemetry from the guest
console with `mosquitto_sub -h 127.0.0.1 -t iotbench/<device>/state -C 1`.
QEMU port forwarding alone does not expose this loopback-only broker.

### Build and boot

From the repository root, validate one target and build it:

```bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe798-hardcoded-credentials'
FIRMWARE=router-cwe798-hardcoded-credentials docker compose run --rm yocto
FIRMWARE=router-cwe798-hardcoded-credentials ./scripts/run-qemu.sh
```

Replace `router` with any supported device. To build all eleven images:

```bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe798-hardcoded-credentials.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
```

The default machine is `qemuarm64`. Set `YOCTO_MACHINE` consistently when
building and booting another supported architecture. Output is exported to
`deploy-images/<device>-cwe798-hardcoded-credentials/<machine>/`, containing
the compressed ext4 rootfs and kernel. `scripts/build-all.sh` includes all new
recipes automatically.

Open `http://127.0.0.1:8080` and use **Vendor Support Backup**. Enter the account
above and choose **Export support backup**. The UI leaves both fields empty
initially. Expected output starts with `HARDCODED_CREDENTIALS_ACCEPTED` and
prints the backup JSON. Incorrect credentials show `Invalid support credentials`.
If port 8080 is occupied, boot with `QEMU_HTTP_PORT=18080` and use
`http://127.0.0.1:18080` in the examples and test client.

### Firmware extraction

From the guest serial console, log in with the root credential documented in
the README and inspect the module:

```bash
sed -n '/const IOTBENCH_SUPPORT_USERNAME/p; /const IOTBENCH_SUPPORT_PASSWORD/p' \
  /usr/share/router-dashboard/modules/hardcoded-credentials/module.php
cat /usr/share/iotbench/hardcoded-credentials/support-backup.json
```

Expected: the two constants show the exact username/password above. They are
the values actually used in `hash_equals()` by the support action.
Serial inspection is evidence of recoverability, not a remote attacker step.

An attacker with only the exported firmware can extract the same values
offline. On a host with `zstd` and the e2fsprogs `debugfs` utility:

```bash
zstd -d \
  deploy-images/router-cwe798-hardcoded-credentials/qemuarm64/iotbench-router-cwe798-hardcoded-credentials-qemuarm64.rootfs.ext4.zst \
  -o /tmp/iotbench-hardcoded-credentials.ext4
debugfs -R 'cat /usr/share/router-dashboard/modules/hardcoded-credentials/module.php' \
  /tmp/iotbench-hardcoded-credentials.ext4
```

This reads the ext4 image without mounting or booting it. Local access to the
firmware file is sufficient; network requests for the module source or the
backup file return HTTP 404 because those files are outside the document root.

### HTTP payloads and expected results

The API is `POST /api.php` with JSON action `support_backup` and header
`X-Dashboard-Token`. A valid request body is:

```json
{"action":"support_backup","username":"support","password":"iotbench-support-2026"}
```

This dependency-free Python example retrieves the public token and performs
the export from a host terminal while QEMU is running:

```bash
python3 - <<'PY'
from html.parser import HTMLParser
import json
import urllib.request

base = "http://127.0.0.1:8080"

class TokenParser(HTMLParser):
    token = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") == "dashboard-token":
            self.token = attrs.get("content")

with urllib.request.urlopen(base + "/", timeout=10) as response:
    page = response.read().decode()
parser = TokenParser()
parser.feed(page)
assert parser.token, "Dashboard token not found"
request = urllib.request.Request(
    base + "/api.php",
    data=json.dumps({"action": "support_backup", "username": "support",
                     "password": "iotbench-support-2026"}).encode(),
    headers={"Content-Type": "application/json",
             "X-Dashboard-Token": parser.token},
)
with urllib.request.urlopen(request, timeout=10) as response:
    print(response.status)
    print(json.dumps(json.load(response), indent=2))
PY
```

Expected: HTTP 200, `ok: true`, `authenticated_as: "support"`, the selected
device class, `signal: "HARDCODED_CREDENTIALS_ACCEPTED"`, and a backup including
`maintenance.backup_scope: "vendor-support-only"` and
`maintenance.inventory_reference: "IOTBENCH-SUPPORT-LAB"`. Peripheral values
can differ across requests because the simulator runs continuously.

| Request condition | Expected HTTP result |
| --- | --- |
| Exact published username and password, valid token | 200; maintenance backup exported |
| Missing, empty or incorrect credentials, valid token | 401; `Invalid support credentials`, no backup |
| Array/object credential or username >64 bytes / password >128 bytes | 422; `Invalid credential format`, no backup |
| Missing or invalid dashboard token | 403 before the action runs |
| Direct URL for the module or backup file | 404 |

Each export checks the credentials again. A successful request does not create
a login session that permits subsequent anonymous exports. There is no SQL,
user-controlled filename or command evaluation: the measured weakness is the
fixed credential used by the actual authentication check.

### Regression verification

With the selected image running, execute:

```bash
python3 scripts/test-hardcoded-credentials.py --device router
# For a different device and host HTTP port:
python3 scripts/test-hardcoded-credentials.py \
  --device plc --url http://127.0.0.1:18080
```

Expected: four `PASS` lines and exit status zero. The client checks the panel,
request-token enforcement, correct/incorrect/missing credentials, malformed
input, repeated authenticated exports, device identity, live peripherals,
the maintenance fixture, direct-file HTTP denial and absence of a persistent
authentication bypass. It requires only Python 3's standard library.

Boot and test each device separately. Repeat after reboot to confirm the
credential is unchanged. Reuse this same client/credential on another device
to demonstrate cross-device access.

### Completed validation

On 2026-10-06, all eleven `qemuarm64` targets passed BitBake parsing,
dependency resolution, actual compilation and export. Every exported image
was booted in QEMU with HVF and the host CPU and passed the HTTP regression
client. The same support credential was accepted across all device profiles.

Native-service checks also passed: HTTP dashboard for the router, JPEG snapshot
and MJPEG stream for the camera, Modbus holding registers 0-3 for the PLC, and
live MQTT state messages on guest loopback for the other eight profiles.
Serial inspection confirmed both `mosquitto` and `iotbench-mqtt` active on
each MQTT device after the systemd build correction.

Offline `debugfs` inspection of all eleven compressed exported root filesystems
confirmed the exact installed module, support fixture and device identity.
Package manifests contained exactly one vulnerability package,
`cwe798-hardcoded-credentials`. Module bytes and embedded credentials were
identical across the eleven exports.

The local report, including kernel/rootfs SHA-256 checksums and offline
inspection results, is
`deploy-images/hardcoded-credentials-qemuarm64-validation.txt`.
Validation used host HTTP port `18080` and Modbus port `11502`; MQTT checks
ran from the guest serial console because the baseline broker is local-only.
Other supported architectures have not been built or boot-tested for this
scenario in this run.

### Remediation and verification

Replace embedded shared credentials with unique credentials enrolled for each
device or user. Store salted password hashes in an access-controlled credential
store, support rotation/revocation, and authorize maintenance exports explicitly.
These changes follow the inbound-authentication guidance in
[MITRE CWE-798](https://cwe.mitre.org/data/definitions/798.html).

Changing a fleet-wide literal or embedding its hash still leaves a shared
credential. Hiding it from the HTML does not address recovery from firmware.
The request token is a separate CSRF control and does not replace authentication.

In a corrected variant, verify that the published support credential no longer
exports the backup, a newly enrolled device credential works, and that credential
fails on another device. Rebuild the sources for lasting changes; default QEMU
snapshots discard guest edits on exit. The supplied regression client's positive
CWE-798 check should fail against that corrected variant.

## Bad SUDO Rights — Path Traversal (CWE-22)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

These eleven fixtures reuse the repository's device profiles, common Yocto
image, architecture selector, build/export scripts and
one-vulnerability-per-image convention. Each `<device>-cwe022-bad-sudo-rights`
recipe installs only `cwe022-bad-sudo-rights` as its vulnerability package. The
local scenario does not attach an action to the shared dashboard or native
device services.

The ground-truth vulnerability is **Path Traversal reachable through an overly
permissive sudo rule / privileged sudo helper**, labeled **CWE-22**. The unsafe
sudo configuration is part of this single scenario, not a second independent
vulnerability label. The attacker position is the synthetic local account
`fixturetest` (UID/GID 994), with a locked password and `/bin/false` login
shell. The guest root console switches to this identity only to simulate the
foothold; no SSH account, password credential or remote entry point is added.

### Shared files and containment

The package source directory is
`meta-iotbench/recipes-vulns/cwe022-bad-sudo-rights/`. Its recipe compiles
`files/maintenance-read.c` with the normal Yocto `${CC}`, `${CFLAGS}` and
`${LDFLAGS}`. The installed reader is root-owned `0755`, with no setuid bit;
only sudo supplies its elevated execution context. The installed policy is
root-owned `0440` at `/etc/sudoers.d/iotbench-maintenance`:

```sudoers
fixturetest ALL=(root) NOPASSWD: /usr/bin/iotbench-maintenance-read /usr/share/iotbench/bad-sudo-rights/data/*
```

The sudo argument wildcard accepts slash characters and parent-directory
segments. The helper checks the raw `.../data/` prefix, one argument and a
240-byte maximum, but deliberately does not canonicalize the path or verify that
its resolved target remains in `data/`. It opens the path with `open()` and
returns at most 65536 bytes from a regular file. It never launches a shell,
executes commands, writes files, installs packages, contacts external systems or
provides persistence. The guest regression script is a separate root-console
test harness, never invoked by the reader.

The root-owned fixture tree is:

```text
/usr/share/iotbench/bad-sudo-rights/          root:root 0755
├── NOTICE                                 0644; exact warning above
├── ground-truth.json                      0644; label, paths, user and signal
├── test-guest.sh                          0644; explicit sh invocation for testing
├── data/                                  0755; intended allowed directory
│   └── status.conf                        0644; synthetic public status
└── private/                               0700
    └── root-only.conf                     0600; fake protected marker
```

Before opening a supplied path the privileged reader calls `chroot()` to this
synthetic tree and `chdir("/")`. This is a lab containment boundary around both
`data/` and `private/`; it deliberately leaves traversal across the **intended
data-directory authorization boundary** possible. Even repeated `../` cannot
read the guest's actual `/etc/passwd`, other firmware system files, or host
files. The tree has no mounts or symlinks and is not writable by `fixturetest`.
Failure to enter containment fails closed. Target symlinks, directories, special
files, extra arguments and oversized paths are rejected. No real secrets or
credentials are installed in the tree. NOTICE is also appended to `/etc/motd` by
`iotbench-bad-sudo-rights.inc` for every fixture image.

This differs from generic vulnerable Java/JAR applications: no Java runtime or
JAR is involved. It differs from generic vulnerable C binaries: this C reader is
the specific command in a real installed sudo policy, with a non-privileged
caller and root-only synthetic target. It differs from ordinary non-privileged
Path Traversal examples: direct access fails for `fixturetest`, while the same
traversal succeeds with `READER_EUID=0` only through the granted sudo operation.
The evidence must include the sudo rule, helper input-to-open flow and
protected-file permissions; a `../` string alone is insufficient.

### Shared build and local testing procedure

From the repository root, parse recipes and resolve one dependency graph:

```bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe022-bad-sudo-rights'
```

Build every fixture using the existing exporter:

```bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe022-bad-sudo-rights.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
```

The normal default is `qemuarm64`. Set `YOCTO_MACHINE` at both build and boot
time for `qemuarm`, `qemux86-64`, `qemux86` or `qemumips`. Exports contain the
kernel and compressed ext4 rootfs under the firmware directories below.
`scripts/build-all.sh` discovers these recipes automatically.

For interactive verification boot a fixture with its per-device command below,
log into the guest serial console using the existing development root account
from the README, and run its guest test command. Expected: five `PASS` lines and
exit status zero. The test verifies a non-root caller, direct private-file read
denial, direct helper denial, normal sudo reading, two traversal variants, root
effective UID, denial of other sudo commands/direct private paths, argument
count, regular-file handling, missing files, shell-shaped filenames, and failure
to escape the synthetic containment root. All reads remain synthetic.

To see the decisive read manually **inside the guest**:

```bash
sudo -n -u fixturetest -- cat /usr/share/iotbench/bad-sudo-rights/private/root-only.conf
# Expected: Permission denied, nonzero exit status.
sudo -n -u fixturetest -- sudo -n /usr/bin/iotbench-maintenance-read \
  /usr/share/iotbench/bad-sudo-rights/data/../private/root-only.conf
# Expected: READER_EUID=0 and ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED.
```

The outer sudo is root's lab harness for changing identity. The inner sudo is
the vulnerable authorization boundary. Do not install this sudo policy or run
the reader with privileges on the host.

The dependency-free POSIX host runner boots a fresh disposable QEMU snapshot,
uses the existing serial login, checks the warning and expected device class,
and runs the installed guest regression without enabling SSH:

```bash
python3 scripts/test-bad-sudo-rights.py --all
# Optional Apple Silicon acceleration and unused host ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-bad-sudo-rights.py --all
```

One image runs at a time. The runner always uses disposable snapshots and logs
the console to the path printed for each device. QEMU and `zstd` must already be
installed. Device-native services remain supplied by their usual device profile;
no new network listener or service sandbox relaxation is part of this fixture.

### Safe remediation shared by all devices

Remove the wildcard sudo grant, or authorize only an exact fixed synthetic
filename (e.g. the absolute `data/status.conf` path). Avoid giving a privileged
reader general path arguments when an operation identifier will suffice. If path
input is required, enforce the intended directory inside the helper: open
relative to a trusted directory descriptor, reject traversal/absolute paths, and
use resolution controls that prevent symlink escape and races. A plain lexical
prefix check is insufficient. Drop unnecessary privileges and retain the outer
lab containment boundary. After rebuilding a corrected variant, the valid
data-file test should succeed while traversal returns a nonzero status without
the protected marker. The vulnerable fixture's positive traversal test must then
fail. Guest snapshot edits are discarded on exit.

### Completed validation

On 2026-10-06, all eleven `qemuarm64` fixtures passed BitBake recipe parsing,
dependency resolution, actual compilation and export. Each image booted in
QEMU with HVF and the host CPU and passed the guest regression (five PASS lines).
Testing used disposable snapshots and host ports HTTP `18080`, MQTT `21883`
and Modbus `11502`; the vulnerability was exercised through the serial console.

Offline `debugfs` inspection of every exported ext4 image confirmed the exact
sudo policy, locked UID/GID 994 account, root-owned `0755` helper (no setuid
bit), `0440` sudoers file, `0700` private directory, `0600` synthetic target,
ground-truth metadata, device identity and required NOTICE/login banner.
Manifests contained exactly one vulnerability package,
`cwe022-bad-sudo-rights`. The compiled helper bytes were identical across all
images.

The [local validation report](../deploy-images/bad-sudo-rights-qemuarm64-validation.txt)
records results, kernel/rootfs/helper SHA-256 checksums and guest console
evidence. Console logs are also saved alongside each exported image as
`validation-console.log`. Other supported architectures have not been built
or boot-tested in this run. Static-analysis entries above describe expected
ground truth; completed validation used build checks, filesystem inspection
and actual sudo execution.

### doorlock-cwe022-bad-sudo-rights

Simulated device: **access-control door lock**, preserving its existing MQTT
lock telemetry and `meta-iotbench/recipes-devices/doorlock/` profile. The
firmware recipe is
`meta-iotbench/recipes-images/iotbench-doorlock-cwe022-bad-sudo-rights.bb`; the
exported firmware directory is
`deploy-images/doorlock-cwe022-bad-sudo-rights/<machine>/`.

Relevant files: `/etc/sudoers.d/iotbench-maintenance`, the privileged
`/usr/bin/iotbench-maintenance-read`, and `NOTICE`, `ground-truth.json`,
`test-guest.sh`, `data/status.conf` and `private/root-only.conf` under
`/usr/share/iotbench/bad-sudo-rights/`. The sudoers rule grants the locked
non-root `fixturetest` account `(root) NOPASSWD` execution of that reader with
`/usr/share/iotbench/bad-sudo-rights/data/*` arguments only. The intended
allowed directory is `/usr/share/iotbench/bad-sudo-rights/data/`.

Path validation is intentionally missing in `maintenance-read.c` between its
lexical prefix check and `open()`: `data/../private/root-only.conf` is not
canonicalized or confined to `data/`. The sudo wildcard accepts that path, and
sudo elevates the helper to root, allowing it to read the synthetic `0600` file
in the `0700` private directory that `fixturetest` cannot read directly. The
helper's outer chroot keeps every read within the synthetic tree.

Expected static-analysis finding: correlate the wildcard sudo grant, root
execution, unvalidated path argument reaching `open()`, and protected-file
permissions to identify privileged directory traversal. Expected ground-truth
label: **CWE-22: Path Traversal reachable through an overly permissive sudo rule
/ privileged sudo helper**. Expected runtime evidence: `READER_EUID=0` and
`ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED`, with direct non-root access denied. Safe
remediation: remove the wildcard grant or allow only the exact data-file
argument, and enforce directory-relative path resolution in the helper as
specified above.

Local build and boot from the repository root:

```bash
FIRMWARE=doorlock-cwe022-bad-sudo-rights docker compose run --rm yocto
FIRMWARE=doorlock-cwe022-bad-sudo-rights ./scripts/run-qemu.sh
```

Local testing from the guest root serial console:

```bash
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh doorlock
```

Alternatively, after building, run from the host (the runner boots the image):

```bash
python3 scripts/test-bad-sudo-rights.py --device doorlock
```

### envsensor-cwe022-bad-sudo-rights

Simulated device: **environmental sensor**, preserving its existing MQTT
environmental telemetry and `meta-iotbench/recipes-devices/envsensor/` profile.
The firmware recipe is
`meta-iotbench/recipes-images/iotbench-envsensor-cwe022-bad-sudo-rights.bb`; the
exported firmware directory is
`deploy-images/envsensor-cwe022-bad-sudo-rights/<machine>/`.

Relevant files: `/etc/sudoers.d/iotbench-maintenance`, the privileged
`/usr/bin/iotbench-maintenance-read`, and `NOTICE`, `ground-truth.json`,
`test-guest.sh`, `data/status.conf` and `private/root-only.conf` under
`/usr/share/iotbench/bad-sudo-rights/`. The sudoers rule grants the locked
non-root `fixturetest` account `(root) NOPASSWD` execution of that reader with
`/usr/share/iotbench/bad-sudo-rights/data/*` arguments only. The intended
allowed directory is `/usr/share/iotbench/bad-sudo-rights/data/`.

Path validation is intentionally missing in `maintenance-read.c` between its
lexical prefix check and `open()`: `data/../private/root-only.conf` is not
canonicalized or confined to `data/`. The sudo wildcard accepts that path, and
sudo elevates the helper to root, allowing it to read the synthetic `0600` file
in the `0700` private directory that `fixturetest` cannot read directly. The
helper's outer chroot keeps every read within the synthetic tree.

Expected static-analysis finding: correlate the wildcard sudo grant, root
execution, unvalidated path argument reaching `open()`, and protected-file
permissions to identify privileged directory traversal. Expected ground-truth
label: **CWE-22: Path Traversal reachable through an overly permissive sudo rule
/ privileged sudo helper**. Expected runtime evidence: `READER_EUID=0` and
`ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED`, with direct non-root access denied. Safe
remediation: remove the wildcard grant or allow only the exact data-file
argument, and enforce directory-relative path resolution in the helper as
specified above.

Local build and boot from the repository root:

```bash
FIRMWARE=envsensor-cwe022-bad-sudo-rights docker compose run --rm yocto
FIRMWARE=envsensor-cwe022-bad-sudo-rights ./scripts/run-qemu.sh
```

Local testing from the guest root serial console:

```bash
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh envsensor
```

Alternatively, after building, run from the host (the runner boots the image):

```bash
python3 scripts/test-bad-sudo-rights.py --device envsensor
```

### healthmonitor-cwe022-bad-sudo-rights

Simulated device: **health monitor**, preserving its existing MQTT synthetic
health telemetry and `meta-iotbench/recipes-devices/healthmonitor/` profile. The
firmware recipe is
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe022-bad-sudo-rights.bb`;
the exported firmware directory is
`deploy-images/healthmonitor-cwe022-bad-sudo-rights/<machine>/`.

Relevant files: `/etc/sudoers.d/iotbench-maintenance`, the privileged
`/usr/bin/iotbench-maintenance-read`, and `NOTICE`, `ground-truth.json`,
`test-guest.sh`, `data/status.conf` and `private/root-only.conf` under
`/usr/share/iotbench/bad-sudo-rights/`. The sudoers rule grants the locked
non-root `fixturetest` account `(root) NOPASSWD` execution of that reader with
`/usr/share/iotbench/bad-sudo-rights/data/*` arguments only. The intended
allowed directory is `/usr/share/iotbench/bad-sudo-rights/data/`.

Path validation is intentionally missing in `maintenance-read.c` between its
lexical prefix check and `open()`: `data/../private/root-only.conf` is not
canonicalized or confined to `data/`. The sudo wildcard accepts that path, and
sudo elevates the helper to root, allowing it to read the synthetic `0600` file
in the `0700` private directory that `fixturetest` cannot read directly. The
helper's outer chroot keeps every read within the synthetic tree.

Expected static-analysis finding: correlate the wildcard sudo grant, root
execution, unvalidated path argument reaching `open()`, and protected-file
permissions to identify privileged directory traversal. Expected ground-truth
label: **CWE-22: Path Traversal reachable through an overly permissive sudo rule
/ privileged sudo helper**. Expected runtime evidence: `READER_EUID=0` and
`ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED`, with direct non-root access denied. Safe
remediation: remove the wildcard grant or allow only the exact data-file
argument, and enforce directory-relative path resolution in the helper as
specified above.

Local build and boot from the repository root:

```bash
FIRMWARE=healthmonitor-cwe022-bad-sudo-rights docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe022-bad-sudo-rights ./scripts/run-qemu.sh
```

Local testing from the guest root serial console:

```bash
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh healthmonitor
```

Alternatively, after building, run from the host (the runner boots the image):

```bash
python3 scripts/test-bad-sudo-rights.py --device healthmonitor
```

### ipcamera-cwe022-bad-sudo-rights

Simulated device: **surveillance IP camera**, preserving its existing HTTP
snapshot/MJPEG simulation and `meta-iotbench/recipes-devices/ipcamera/` profile.
The firmware recipe is
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe022-bad-sudo-rights.bb`; the
exported firmware directory is
`deploy-images/ipcamera-cwe022-bad-sudo-rights/<machine>/`.

Relevant files: `/etc/sudoers.d/iotbench-maintenance`, the privileged
`/usr/bin/iotbench-maintenance-read`, and `NOTICE`, `ground-truth.json`,
`test-guest.sh`, `data/status.conf` and `private/root-only.conf` under
`/usr/share/iotbench/bad-sudo-rights/`. The sudoers rule grants the locked
non-root `fixturetest` account `(root) NOPASSWD` execution of that reader with
`/usr/share/iotbench/bad-sudo-rights/data/*` arguments only. The intended
allowed directory is `/usr/share/iotbench/bad-sudo-rights/data/`.

Path validation is intentionally missing in `maintenance-read.c` between its
lexical prefix check and `open()`: `data/../private/root-only.conf` is not
canonicalized or confined to `data/`. The sudo wildcard accepts that path, and
sudo elevates the helper to root, allowing it to read the synthetic `0600` file
in the `0700` private directory that `fixturetest` cannot read directly. The
helper's outer chroot keeps every read within the synthetic tree.

Expected static-analysis finding: correlate the wildcard sudo grant, root
execution, unvalidated path argument reaching `open()`, and protected-file
permissions to identify privileged directory traversal. Expected ground-truth
label: **CWE-22: Path Traversal reachable through an overly permissive sudo rule
/ privileged sudo helper**. Expected runtime evidence: `READER_EUID=0` and
`ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED`, with direct non-root access denied. Safe
remediation: remove the wildcard grant or allow only the exact data-file
argument, and enforce directory-relative path resolution in the helper as
specified above.

Local build and boot from the repository root:

```bash
FIRMWARE=ipcamera-cwe022-bad-sudo-rights docker compose run --rm yocto
FIRMWARE=ipcamera-cwe022-bad-sudo-rights ./scripts/run-qemu.sh
```

Local testing from the guest root serial console:

```bash
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh ipcamera
```

Alternatively, after building, run from the host (the runner boots the image):

```bash
python3 scripts/test-bad-sudo-rights.py --device ipcamera
```

### plc-cwe022-bad-sudo-rights

Simulated device: **industrial PLC gateway (OT)**, preserving its existing
Modbus/TCP peripheral registers and `meta-iotbench/recipes-devices/plc/`
profile. The firmware recipe is
`meta-iotbench/recipes-images/iotbench-plc-cwe022-bad-sudo-rights.bb`; the
exported firmware directory is
`deploy-images/plc-cwe022-bad-sudo-rights/<machine>/`.

Relevant files: `/etc/sudoers.d/iotbench-maintenance`, the privileged
`/usr/bin/iotbench-maintenance-read`, and `NOTICE`, `ground-truth.json`,
`test-guest.sh`, `data/status.conf` and `private/root-only.conf` under
`/usr/share/iotbench/bad-sudo-rights/`. The sudoers rule grants the locked
non-root `fixturetest` account `(root) NOPASSWD` execution of that reader with
`/usr/share/iotbench/bad-sudo-rights/data/*` arguments only. The intended
allowed directory is `/usr/share/iotbench/bad-sudo-rights/data/`.

Path validation is intentionally missing in `maintenance-read.c` between its
lexical prefix check and `open()`: `data/../private/root-only.conf` is not
canonicalized or confined to `data/`. The sudo wildcard accepts that path, and
sudo elevates the helper to root, allowing it to read the synthetic `0600` file
in the `0700` private directory that `fixturetest` cannot read directly. The
helper's outer chroot keeps every read within the synthetic tree.

Expected static-analysis finding: correlate the wildcard sudo grant, root
execution, unvalidated path argument reaching `open()`, and protected-file
permissions to identify privileged directory traversal. Expected ground-truth
label: **CWE-22: Path Traversal reachable through an overly permissive sudo rule
/ privileged sudo helper**. Expected runtime evidence: `READER_EUID=0` and
`ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED`, with direct non-root access denied. Safe
remediation: remove the wildcard grant or allow only the exact data-file
argument, and enforce directory-relative path resolution in the helper as
specified above.

Local build and boot from the repository root:

```bash
FIRMWARE=plc-cwe022-bad-sudo-rights docker compose run --rm yocto
FIRMWARE=plc-cwe022-bad-sudo-rights ./scripts/run-qemu.sh
```

Local testing from the guest root serial console:

```bash
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh plc
```

Alternatively, after building, run from the host (the runner boots the image):

```bash
python3 scripts/test-bad-sudo-rights.py --device plc
```

### router-cwe022-bad-sudo-rights

Simulated device: **network gateway/router**, preserving its existing shared
HTTP administration and `meta-iotbench/recipes-devices/router/` profile. The
firmware recipe is
`meta-iotbench/recipes-images/iotbench-router-cwe022-bad-sudo-rights.bb`; the
exported firmware directory is
`deploy-images/router-cwe022-bad-sudo-rights/<machine>/`.

Relevant files: `/etc/sudoers.d/iotbench-maintenance`, the privileged
`/usr/bin/iotbench-maintenance-read`, and `NOTICE`, `ground-truth.json`,
`test-guest.sh`, `data/status.conf` and `private/root-only.conf` under
`/usr/share/iotbench/bad-sudo-rights/`. The sudoers rule grants the locked
non-root `fixturetest` account `(root) NOPASSWD` execution of that reader with
`/usr/share/iotbench/bad-sudo-rights/data/*` arguments only. The intended
allowed directory is `/usr/share/iotbench/bad-sudo-rights/data/`.

Path validation is intentionally missing in `maintenance-read.c` between its
lexical prefix check and `open()`: `data/../private/root-only.conf` is not
canonicalized or confined to `data/`. The sudo wildcard accepts that path, and
sudo elevates the helper to root, allowing it to read the synthetic `0600` file
in the `0700` private directory that `fixturetest` cannot read directly. The
helper's outer chroot keeps every read within the synthetic tree.

Expected static-analysis finding: correlate the wildcard sudo grant, root
execution, unvalidated path argument reaching `open()`, and protected-file
permissions to identify privileged directory traversal. Expected ground-truth
label: **CWE-22: Path Traversal reachable through an overly permissive sudo rule
/ privileged sudo helper**. Expected runtime evidence: `READER_EUID=0` and
`ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED`, with direct non-root access denied. Safe
remediation: remove the wildcard grant or allow only the exact data-file
argument, and enforce directory-relative path resolution in the helper as
specified above.

Local build and boot from the repository root:

```bash
FIRMWARE=router-cwe022-bad-sudo-rights docker compose run --rm yocto
FIRMWARE=router-cwe022-bad-sudo-rights ./scripts/run-qemu.sh
```

Local testing from the guest root serial console:

```bash
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh router
```

Alternatively, after building, run from the host (the runner boots the image):

```bash
python3 scripts/test-bad-sudo-rights.py --device router
```

### smartbulb-cwe022-bad-sudo-rights

Simulated device: **lighting smart bulb**, preserving its existing MQTT lighting
telemetry and `meta-iotbench/recipes-devices/smartbulb/` profile. The firmware
recipe is
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe022-bad-sudo-rights.bb`; the
exported firmware directory is
`deploy-images/smartbulb-cwe022-bad-sudo-rights/<machine>/`.

Relevant files: `/etc/sudoers.d/iotbench-maintenance`, the privileged
`/usr/bin/iotbench-maintenance-read`, and `NOTICE`, `ground-truth.json`,
`test-guest.sh`, `data/status.conf` and `private/root-only.conf` under
`/usr/share/iotbench/bad-sudo-rights/`. The sudoers rule grants the locked
non-root `fixturetest` account `(root) NOPASSWD` execution of that reader with
`/usr/share/iotbench/bad-sudo-rights/data/*` arguments only. The intended
allowed directory is `/usr/share/iotbench/bad-sudo-rights/data/`.

Path validation is intentionally missing in `maintenance-read.c` between its
lexical prefix check and `open()`: `data/../private/root-only.conf` is not
canonicalized or confined to `data/`. The sudo wildcard accepts that path, and
sudo elevates the helper to root, allowing it to read the synthetic `0600` file
in the `0700` private directory that `fixturetest` cannot read directly. The
helper's outer chroot keeps every read within the synthetic tree.

Expected static-analysis finding: correlate the wildcard sudo grant, root
execution, unvalidated path argument reaching `open()`, and protected-file
permissions to identify privileged directory traversal. Expected ground-truth
label: **CWE-22: Path Traversal reachable through an overly permissive sudo rule
/ privileged sudo helper**. Expected runtime evidence: `READER_EUID=0` and
`ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED`, with direct non-root access denied. Safe
remediation: remove the wildcard grant or allow only the exact data-file
argument, and enforce directory-relative path resolution in the helper as
specified above.

Local build and boot from the repository root:

```bash
FIRMWARE=smartbulb-cwe022-bad-sudo-rights docker compose run --rm yocto
FIRMWARE=smartbulb-cwe022-bad-sudo-rights ./scripts/run-qemu.sh
```

Local testing from the guest root serial console:

```bash
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh smartbulb
```

Alternatively, after building, run from the host (the runner boots the image):

```bash
python3 scripts/test-bad-sudo-rights.py --device smartbulb
```

### smarthub-cwe022-bad-sudo-rights

Simulated device: **controller/smart hub**, preserving its existing MQTT hub
telemetry and `meta-iotbench/recipes-devices/smarthub/` profile. The firmware
recipe is
`meta-iotbench/recipes-images/iotbench-smarthub-cwe022-bad-sudo-rights.bb`; the
exported firmware directory is
`deploy-images/smarthub-cwe022-bad-sudo-rights/<machine>/`.

Relevant files: `/etc/sudoers.d/iotbench-maintenance`, the privileged
`/usr/bin/iotbench-maintenance-read`, and `NOTICE`, `ground-truth.json`,
`test-guest.sh`, `data/status.conf` and `private/root-only.conf` under
`/usr/share/iotbench/bad-sudo-rights/`. The sudoers rule grants the locked
non-root `fixturetest` account `(root) NOPASSWD` execution of that reader with
`/usr/share/iotbench/bad-sudo-rights/data/*` arguments only. The intended
allowed directory is `/usr/share/iotbench/bad-sudo-rights/data/`.

Path validation is intentionally missing in `maintenance-read.c` between its
lexical prefix check and `open()`: `data/../private/root-only.conf` is not
canonicalized or confined to `data/`. The sudo wildcard accepts that path, and
sudo elevates the helper to root, allowing it to read the synthetic `0600` file
in the `0700` private directory that `fixturetest` cannot read directly. The
helper's outer chroot keeps every read within the synthetic tree.

Expected static-analysis finding: correlate the wildcard sudo grant, root
execution, unvalidated path argument reaching `open()`, and protected-file
permissions to identify privileged directory traversal. Expected ground-truth
label: **CWE-22: Path Traversal reachable through an overly permissive sudo rule
/ privileged sudo helper**. Expected runtime evidence: `READER_EUID=0` and
`ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED`, with direct non-root access denied. Safe
remediation: remove the wildcard grant or allow only the exact data-file
argument, and enforce directory-relative path resolution in the helper as
specified above.

Local build and boot from the repository root:

```bash
FIRMWARE=smarthub-cwe022-bad-sudo-rights docker compose run --rm yocto
FIRMWARE=smarthub-cwe022-bad-sudo-rights ./scripts/run-qemu.sh
```

Local testing from the guest root serial console:

```bash
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh smarthub
```

Alternatively, after building, run from the host (the runner boots the image):

```bash
python3 scripts/test-bad-sudo-rights.py --device smarthub
```

### smartplug-cwe022-bad-sudo-rights

Simulated device: **energy-management smart plug**, preserving its existing MQTT
power telemetry and `meta-iotbench/recipes-devices/smartplug/` profile. The
firmware recipe is
`meta-iotbench/recipes-images/iotbench-smartplug-cwe022-bad-sudo-rights.bb`; the
exported firmware directory is
`deploy-images/smartplug-cwe022-bad-sudo-rights/<machine>/`.

Relevant files: `/etc/sudoers.d/iotbench-maintenance`, the privileged
`/usr/bin/iotbench-maintenance-read`, and `NOTICE`, `ground-truth.json`,
`test-guest.sh`, `data/status.conf` and `private/root-only.conf` under
`/usr/share/iotbench/bad-sudo-rights/`. The sudoers rule grants the locked
non-root `fixturetest` account `(root) NOPASSWD` execution of that reader with
`/usr/share/iotbench/bad-sudo-rights/data/*` arguments only. The intended
allowed directory is `/usr/share/iotbench/bad-sudo-rights/data/`.

Path validation is intentionally missing in `maintenance-read.c` between its
lexical prefix check and `open()`: `data/../private/root-only.conf` is not
canonicalized or confined to `data/`. The sudo wildcard accepts that path, and
sudo elevates the helper to root, allowing it to read the synthetic `0600` file
in the `0700` private directory that `fixturetest` cannot read directly. The
helper's outer chroot keeps every read within the synthetic tree.

Expected static-analysis finding: correlate the wildcard sudo grant, root
execution, unvalidated path argument reaching `open()`, and protected-file
permissions to identify privileged directory traversal. Expected ground-truth
label: **CWE-22: Path Traversal reachable through an overly permissive sudo rule
/ privileged sudo helper**. Expected runtime evidence: `READER_EUID=0` and
`ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED`, with direct non-root access denied. Safe
remediation: remove the wildcard grant or allow only the exact data-file
argument, and enforce directory-relative path resolution in the helper as
specified above.

Local build and boot from the repository root:

```bash
FIRMWARE=smartplug-cwe022-bad-sudo-rights docker compose run --rm yocto
FIRMWARE=smartplug-cwe022-bad-sudo-rights ./scripts/run-qemu.sh
```

Local testing from the guest root serial console:

```bash
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh smartplug
```

Alternatively, after building, run from the host (the runner boots the image):

```bash
python3 scripts/test-bad-sudo-rights.py --device smartplug
```

### smartspeaker-cwe022-bad-sudo-rights

Simulated device: **audio/voice-assistant smart speaker**, preserving its
existing MQTT audio telemetry and `meta-iotbench/recipes-devices/smartspeaker/`
profile. The firmware recipe is
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe022-bad-sudo-rights.bb`;
the exported firmware directory is
`deploy-images/smartspeaker-cwe022-bad-sudo-rights/<machine>/`.

Relevant files: `/etc/sudoers.d/iotbench-maintenance`, the privileged
`/usr/bin/iotbench-maintenance-read`, and `NOTICE`, `ground-truth.json`,
`test-guest.sh`, `data/status.conf` and `private/root-only.conf` under
`/usr/share/iotbench/bad-sudo-rights/`. The sudoers rule grants the locked
non-root `fixturetest` account `(root) NOPASSWD` execution of that reader with
`/usr/share/iotbench/bad-sudo-rights/data/*` arguments only. The intended
allowed directory is `/usr/share/iotbench/bad-sudo-rights/data/`.

Path validation is intentionally missing in `maintenance-read.c` between its
lexical prefix check and `open()`: `data/../private/root-only.conf` is not
canonicalized or confined to `data/`. The sudo wildcard accepts that path, and
sudo elevates the helper to root, allowing it to read the synthetic `0600` file
in the `0700` private directory that `fixturetest` cannot read directly. The
helper's outer chroot keeps every read within the synthetic tree.

Expected static-analysis finding: correlate the wildcard sudo grant, root
execution, unvalidated path argument reaching `open()`, and protected-file
permissions to identify privileged directory traversal. Expected ground-truth
label: **CWE-22: Path Traversal reachable through an overly permissive sudo rule
/ privileged sudo helper**. Expected runtime evidence: `READER_EUID=0` and
`ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED`, with direct non-root access denied. Safe
remediation: remove the wildcard grant or allow only the exact data-file
argument, and enforce directory-relative path resolution in the helper as
specified above.

Local build and boot from the repository root:

```bash
FIRMWARE=smartspeaker-cwe022-bad-sudo-rights docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe022-bad-sudo-rights ./scripts/run-qemu.sh
```

Local testing from the guest root serial console:

```bash
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh smartspeaker
```

Alternatively, after building, run from the host (the runner boots the image):

```bash
python3 scripts/test-bad-sudo-rights.py --device smartspeaker
```

### thermostat-cwe022-bad-sudo-rights

Simulated device: **climate-control thermostat**, preserving its existing MQTT
climate telemetry and `meta-iotbench/recipes-devices/thermostat/` profile. The
firmware recipe is
`meta-iotbench/recipes-images/iotbench-thermostat-cwe022-bad-sudo-rights.bb`;
the exported firmware directory is
`deploy-images/thermostat-cwe022-bad-sudo-rights/<machine>/`.

Relevant files: `/etc/sudoers.d/iotbench-maintenance`, the privileged
`/usr/bin/iotbench-maintenance-read`, and `NOTICE`, `ground-truth.json`,
`test-guest.sh`, `data/status.conf` and `private/root-only.conf` under
`/usr/share/iotbench/bad-sudo-rights/`. The sudoers rule grants the locked
non-root `fixturetest` account `(root) NOPASSWD` execution of that reader with
`/usr/share/iotbench/bad-sudo-rights/data/*` arguments only. The intended
allowed directory is `/usr/share/iotbench/bad-sudo-rights/data/`.

Path validation is intentionally missing in `maintenance-read.c` between its
lexical prefix check and `open()`: `data/../private/root-only.conf` is not
canonicalized or confined to `data/`. The sudo wildcard accepts that path, and
sudo elevates the helper to root, allowing it to read the synthetic `0600` file
in the `0700` private directory that `fixturetest` cannot read directly. The
helper's outer chroot keeps every read within the synthetic tree.

Expected static-analysis finding: correlate the wildcard sudo grant, root
execution, unvalidated path argument reaching `open()`, and protected-file
permissions to identify privileged directory traversal. Expected ground-truth
label: **CWE-22: Path Traversal reachable through an overly permissive sudo rule
/ privileged sudo helper**. Expected runtime evidence: `READER_EUID=0` and
`ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED`, with direct non-root access denied. Safe
remediation: remove the wildcard grant or allow only the exact data-file
argument, and enforce directory-relative path resolution in the helper as
specified above.

Local build and boot from the repository root:

```bash
FIRMWARE=thermostat-cwe022-bad-sudo-rights docker compose run --rm yocto
FIRMWARE=thermostat-cwe022-bad-sudo-rights ./scripts/run-qemu.sh
```

Local testing from the guest root serial console:

```bash
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh thermostat
```

Alternatively, after building, run from the host (the runner boots the image):

```bash
python3 scripts/test-bad-sudo-rights.py --device thermostat
```

## Privilege Escalation Risk — Dangerous SUID Rights (CWE-250)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scope and ground truth

These eleven fixtures model **Privilege escalation risk caused by dangerous SUID
rights**. Each existing device profile is combined with only
`cwe250-dangerous-suid-rights` as its vulnerability package, using the normal
Yocto image, build scripts and architecture selector. The target is a dedicated
synthetic ELF executable, `/usr/bin/iotbench-suid-fixture`, created for this
benchmark. No existing system utility is made SUID by this scenario.

The expected ground-truth label is **Privilege escalation risk caused by
dangerous SUID rights**, classified as [CWE-250: Execution with Unnecessary
Privileges](https://cwe.mitre.org/data/definitions/250.html). This helper needs
no elevated privilege to print a static marker and execution identity, yet its
installed SUID bit gives it root's effective UID when an unprivileged user
executes it. The spreadsheet's legacy Bad SUID Rights row uses CWE-306; this
implementation uses CWE-250 because its measured defect is unnecessary
privilege, not an authentication function.

The fixture focuses on **filesystem permissions and privilege boundaries**. It
supplies no working privilege-escalation exploit or exploitation chain.
Reporting effective UID 0 confirms the kernel's SUID transition for this
harmless helper; it does not supply a privileged shell or arbitrary root
operations. SUID alone is not evidence that every program is exploitable: this
known-positive sample is intentionally unnecessary privilege on a synthetic
program whose entire function is safe without it.

### Installed files and behavior

| Item | Installed path / value |
| --- | --- |
| Synthetic executable | `/usr/bin/iotbench-suid-fixture` |
| Owner / group | `root:root`, numeric UID/GID `0:0` |
| Permission mode | `4755`, displayed as `-rwsr-xr-x` |
| SUID / SGID | SUID enabled (`04000`); SGID disabled |
| Unprivileged caller | `suidfixture`, UID/GID `993:993`, no privileged supplementary groups |
| Account state | Locked password, `/bin/false` shell, no login credentials |
| Fixture notice | `/usr/share/iotbench/dangerous-suid-rights/NOTICE` |
| Ground truth | `/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` |
| Login warning | Same NOTICE appended to `/etc/motd` |

The `s` in the owner's execute position means SUID is enabled together with
owner execution permission. The group and other `r-x` permissions allow a normal
unprivileged caller to run the helper. Its root-owned parent directories are
traversable and not publicly writable; the helper itself is not writable by the
fixture user. The intentionally dangerous permission is **unnecessary SUID**,
not a writable program or a writable system directory.

`iotbench-suid-fixture.c` is compiled with the standard Yocto `${CC}`,
`${CFLAGS}` and `${LDFLAGS}`. Installation sets root ownership before applying
`chmod 4755`, since changing ownership can clear SUID. A rootfs postprocess
check fails image generation unless ownership and mode are exactly `0:0:4755`.
Final ext4 inode metadata is verified separately with `debugfs`.

The helper accepts no arguments and reads no stdin or filesystem files. It
prints the warning, the fixed marker `SUID_FIXTURE_ONLY=BENIGN_IDENTITY_REPORT`,
and its real/effective UID/GID, then exits. Additional arguments are rejected
with status 2. It never launches another program, invokes a shell or
interpreter, accepts commands or paths, modifies authentication files or
sudoers, accesses host files, performs networking or provides persistence. It
contains no credentials or secrets. The fixture adds no daemon or web module and
keeps the device's existing native telemetry services.

`util-linux-setpriv` is installed as an ordinary **non-SUID** verification
utility with mode `0755`; it is not the benchmark target. From the existing
guest root console it switches to the synthetic non-root UID/GID and directly
executes the test helper. The helper itself never calls this utility. User
creation uses Yocto's existing `useradd` class; no runtime account changes or
additional login credentials are part of the helper.

### Local build and verification

From the repository root, parse and resolve one image:

```bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe250-dangerous-suid-rights'
```

Build all eleven fixtures through the existing exporter:

```bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe250-dangerous-suid-rights.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
```

The default architecture is `qemuarm64`. Other existing selectors are `qemuarm`,
`qemux86-64`, `qemux86` and `qemumips`; set `YOCTO_MACHINE` consistently for
build and boot. `scripts/build-all.sh` discovers the new recipes automatically.
Each firmware directory below contains its compressed ext4 image and kernel.

For **static verification without booting**, use the new dependency-free
verification script on a host with Python 3, `debugfs` and `zstd`:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/router-cwe250-dangerous-suid-rights/qemuarm64/iotbench-router-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Expected: two `PASS` lines. This checks the real ext4 inode metadata and
accessible parent directories, the locked non-root account, a dedicated ELF
helper, matching ground truth, device identity and the warning. It does not
mount the firmware or execute its contents on the host. Use `--debugfs` to
specify the tool's absolute path when it is not on PATH. The existing builder
also provides the inspection tools:

```bash
docker compose run --rm yocto python3 /scripts/test-dangerous-suid-rights.py \
  --image /export/router-cwe250-dangerous-suid-rights/qemuarm64/iotbench-router-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

For **benign runtime verification**, boot one image with the per-device commands
below and use its root serial console. The root login is the existing lab
account from the README. Inspect metadata and run the helper with the normal
non-root caller identity:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected metadata: `root:root 4755 -rwsr-xr-x`. Expected helper output:

```text
INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
SUID_FIXTURE_ONLY=BENIGN_IDENTITY_REPORT
REAL_UID=993
EFFECTIVE_UID=0
REAL_GID=993
EFFECTIVE_GID=993
```

The real UID identifies the non-root caller; the effective UID becomes the file
owner's UID because SUID is enabled. The group remains the caller's group
because SGID is disabled. Running the helper directly as root does not establish
this boundary transition. Runtime SUID effects can be suppressed by `nosuid`
mounts, `no_new_privs` or tracing; static metadata remains the primary finding.

To automate the console checks on a POSIX host with QEMU and `zstd`:

```bash
python3 scripts/test-dangerous-suid-rights.py --device router
python3 scripts/test-dangerous-suid-rights.py --all
# Optional Apple Silicon acceleration and unused host ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-dangerous-suid-rights.py --all
```

This runner boots and closes each disposable QEMU snapshot itself. It checks
metadata, the device profile, real/effective identities, the static marker and
rejection of an extra argument. Console logs go to the path printed for each
image. All helper execution takes place inside the guest.

### Expected static-analysis finding and secure remediation

A firmware analyzer should report the synthetic executable's root owner, execute
bits, SUID bit and accessibility to a non-root user. Correlate those inode facts
with the installed ground truth and the helper's lack of any need for root
privileges. A filename or an ELF string alone is not sufficient: inspection or
extraction must preserve numeric ownership and permission bits.

Secure remediation is to install this helper as `root:root` with mode `0755`
instead of `4755`, removing SUID while retaining normal execution. Apply the
change in the recipe and update the intentionally vulnerable rootfs assertion
for a corrected variant, then rebuild. No elevated capability is needed for this
helper. In a disposable guest only, a quick comparison is:

```bash
chmod 0755 /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

The static marker should still print, but both `REAL_UID` and `EFFECTIVE_UID`
should be `993`; metadata should read `root:root 755 -rwxr-xr-x`. The supplied
known-positive regression should then fail its SUID assertions. Default guest
snapshot changes are discarded; source changes and a rebuild provide the lasting
corrected variant.

### Completed validation

On 2026-10-06, all eleven `qemuarm64` targets passed BitBake parsing, dependency
resolution, actual compilation and export. Each exported image passed the
offline verifier against its real ext4 inode metadata: the synthetic ELF
helper was root-owned `0:0`, mode `4755`, executable by non-root callers, with
accessible and non-writable parent directories. Account, ground-truth and
warning checks passed for every device; the verification utility remained
non-SUID `0755`. Both compressed and uncompressed image inspection were checked.

Package manifests contained exactly one vulnerability package,
`cwe250-dangerous-suid-rights`. Helper bytes were identical across all eleven
images. No sudo permission rule was introduced by this scenario.

Every image also booted in a disposable QEMU snapshot using HVF and the host
CPU. The benign identity test confirmed `REAL_UID=993`, `EFFECTIVE_UID=0`,
`REAL_GID=993`, `EFFECTIVE_GID=993`, the expected static marker, correct device
identity and rejection of additional arguments with exit status 2. Host ports
were HTTP `18080`, MQTT `21883` and Modbus `11502`.

The [local validation report](../deploy-images/dangerous-suid-rights-qemuarm64-validation.txt)
contains results, kernel/rootfs/helper SHA-256 checksums and console evidence.
Each exported firmware directory also contains `validation-console.log`.
Other supported architectures have not been built or boot-tested in this run.
The documented analyzer finding is expected ground truth; completed validation
used inode inspection and benign identity reporting, without an exploitation
chain or an external firmware-analysis engine.

### doorlock-cwe250-dangerous-suid-rights

Simulated device: **access-control door lock**, retaining its existing MQTT lock
telemetry and `meta-iotbench/recipes-devices/doorlock/` profile. Image recipe:
`meta-iotbench/recipes-images/iotbench-doorlock-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/doorlock-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/doorlock-cwe250-dangerous-suid-rights/qemuarm64/iotbench-doorlock-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=doorlock-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=doorlock-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/doorlock-cwe250-dangerous-suid-rights/qemuarm64/iotbench-doorlock-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device doorlock
```

### envsensor-cwe250-dangerous-suid-rights

Simulated device: **environmental sensor**, retaining its existing MQTT
environmental telemetry and `meta-iotbench/recipes-devices/envsensor/` profile.
Image recipe:
`meta-iotbench/recipes-images/iotbench-envsensor-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/envsensor-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/envsensor-cwe250-dangerous-suid-rights/qemuarm64/iotbench-envsensor-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=envsensor-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=envsensor-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/envsensor-cwe250-dangerous-suid-rights/qemuarm64/iotbench-envsensor-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device envsensor
```

### healthmonitor-cwe250-dangerous-suid-rights

Simulated device: **health monitor**, retaining its existing MQTT synthetic
health telemetry and `meta-iotbench/recipes-devices/healthmonitor/` profile.
Image recipe:
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/healthmonitor-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/healthmonitor-cwe250-dangerous-suid-rights/qemuarm64/iotbench-healthmonitor-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=healthmonitor-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/healthmonitor-cwe250-dangerous-suid-rights/qemuarm64/iotbench-healthmonitor-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device healthmonitor
```

### ipcamera-cwe250-dangerous-suid-rights

Simulated device: **surveillance IP camera**, retaining its existing HTTP
snapshots and MJPEG streaming and `meta-iotbench/recipes-devices/ipcamera/`
profile. Image recipe:
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/ipcamera-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/ipcamera-cwe250-dangerous-suid-rights/qemuarm64/iotbench-ipcamera-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=ipcamera-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=ipcamera-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/ipcamera-cwe250-dangerous-suid-rights/qemuarm64/iotbench-ipcamera-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device ipcamera
```

### plc-cwe250-dangerous-suid-rights

Simulated device: **industrial PLC gateway (OT)**, retaining its existing
Modbus/TCP registers and `meta-iotbench/recipes-devices/plc/` profile. Image
recipe:
`meta-iotbench/recipes-images/iotbench-plc-cwe250-dangerous-suid-rights.bb`.
Firmware directory: `deploy-images/plc-cwe250-dangerous-suid-rights/<machine>/`.
For the default machine, the rootfs is
`deploy-images/plc-cwe250-dangerous-suid-rights/qemuarm64/iotbench-plc-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=plc-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=plc-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/plc-cwe250-dangerous-suid-rights/qemuarm64/iotbench-plc-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device plc
```

### router-cwe250-dangerous-suid-rights

Simulated device: **network gateway/router**, retaining its existing shared HTTP
administration and `meta-iotbench/recipes-devices/router/` profile. Image
recipe:
`meta-iotbench/recipes-images/iotbench-router-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/router-cwe250-dangerous-suid-rights/<machine>/`. For the default
machine, the rootfs is
`deploy-images/router-cwe250-dangerous-suid-rights/qemuarm64/iotbench-router-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=router-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=router-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/router-cwe250-dangerous-suid-rights/qemuarm64/iotbench-router-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device router
```

### smartbulb-cwe250-dangerous-suid-rights

Simulated device: **lighting smart bulb**, retaining its existing MQTT lighting
telemetry and `meta-iotbench/recipes-devices/smartbulb/` profile. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/smartbulb-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/smartbulb-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smartbulb-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=smartbulb-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=smartbulb-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/smartbulb-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smartbulb-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device smartbulb
```

### smarthub-cwe250-dangerous-suid-rights

Simulated device: **controller/smart hub**, retaining its existing MQTT hub
telemetry and `meta-iotbench/recipes-devices/smarthub/` profile. Image recipe:
`meta-iotbench/recipes-images/iotbench-smarthub-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/smarthub-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/smarthub-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smarthub-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=smarthub-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=smarthub-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/smarthub-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smarthub-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device smarthub
```

### smartplug-cwe250-dangerous-suid-rights

Simulated device: **energy-management smart plug**, retaining its existing MQTT
power telemetry and `meta-iotbench/recipes-devices/smartplug/` profile. Image
recipe:
`meta-iotbench/recipes-images/iotbench-smartplug-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/smartplug-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/smartplug-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smartplug-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=smartplug-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=smartplug-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/smartplug-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smartplug-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device smartplug
```

### smartspeaker-cwe250-dangerous-suid-rights

Simulated device: **audio/voice-assistant smart speaker**, retaining its
existing MQTT audio telemetry and `meta-iotbench/recipes-devices/smartspeaker/`
profile. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/smartspeaker-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/smartspeaker-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smartspeaker-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=smartspeaker-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/smartspeaker-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smartspeaker-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device smartspeaker
```

### thermostat-cwe250-dangerous-suid-rights

Simulated device: **climate-control thermostat**, retaining its existing MQTT
climate telemetry and `meta-iotbench/recipes-devices/thermostat/` profile. Image
recipe:
`meta-iotbench/recipes-images/iotbench-thermostat-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/thermostat-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/thermostat-cwe250-dangerous-suid-rights/qemuarm64/iotbench-thermostat-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=thermostat-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=thermostat-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/thermostat-cwe250-dangerous-suid-rights/qemuarm64/iotbench-thermostat-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device thermostat
```


## Hardcoded Credentials — Hardcoding User Passwords (CWE-798)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario and actual authentication evidence

The eleven `<device>-cwe798-hardcoded-user-passwords` images combine the
existing common image and corresponding device profile with exactly one
vulnerability package, `cwe798-hardcoded-user-passwords`. This is separate from
the HTTP vendor-support images documented earlier. The package adds local
application authentication and requires no network connection or remote login.
The shared dashboard, simulator and native telemetry are supplied by the normal
device profiles; this fixture adds no service, web action or network listener.

The modeled vulnerability is specifically **a fixed synthetic user password
embedded directly in the firmware and reused deterministically, resulting in
CWE-798: Use of Hard-coded Credentials**. The exact expected ground-truth label
is **Hardcoded credentials — Hardcoding the user passwords**. The corresponding
weakness is **CWE-798 — Use of Hard-coded Credentials**.

The local application account is `fixtureuser`. Its fake, fixture-exclusive
password is `fixture-password-123`. The source account database is
`meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/files/accounts.conf`:

~~~text
fixtureuser:fixture-password-123
~~~

The recipe copies these bytes verbatim into
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` during `do_install`.
The file format is one `username:plaintext-password` record. No random password,
per-device input, environment override, installer enrollment, postinstall hook
or first-boot provisioning supplies this credential. Every fresh image, copied
image and installation therefore begins with the same account and password,
including across device types and architectures. Device identity and peripheral
specifications remain device-specific; the fixture account record is identical.

The installed `/usr/bin/iotbench-fixture-auth` is the actual credential
consumer. It reads the fixed account database using `IFS=: read -r`, reads the
submitted password from stdin and compares both the submitted account name and
password with the stored fields. Only a match prints
`HARDCODED_USER_PASSWORD_ACCEPTED`, `AUTHENTICATED_AS=fixtureuser` and the
benign marker `FIXTURE_ONLY=BENIGN_LOCAL_AUTHENTICATION`, exiting zero.
A wrong username or password, empty input or stdin EOF exits 1 without the
success marker. Missing/empty account storage or a wrong argument count exits 2.
The input password must be a newline-terminated line; all inputs are treated as
data, never sourced, evaluated, used as filenames or executed.

This is a synthetic **application account**, following the existing CWE-798
application-identity convention. It does not create an OS user, alter
`/etc/passwd` or `/etc/shadow`, grant a shell, run a command on authentication,
change privileges or store a login session. The helper only reads its fixed
configuration and prints a marker. Run it from the existing guest root serial
console to read the root-only database; authenticating `fixtureuser` grants no
root privilege. Serial-console development credentials belong to the common
image and are separate from the measured fixture account.

### Firmware components and permissions

The vulnerability directory is
`meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`. The recipe uses
local `file://` sources, `S = "${UNPACKDIR}"`, standard Yocto path variables
and the already available BusyBox shell; it adds no layer or source download.
It marks the account database as a configuration file. Source edits followed by
a rebuild change a fixture variant; there is no automatic password change.

| Source under the vulnerability directory | Firmware component / role |
| --- | --- |
| `cwe798-hardcoded-user-passwords_1.0.bb` | Installs the account record verbatim and the local authentication consumer |
| `files/accounts.conf` | `/etc/iotbench/hardcoded-user-passwords/accounts.conf`, root:root `0600`; actual synthetic account/password |
| `files/iotbench-fixture-auth` | `/usr/bin/iotbench-fixture-auth`, root:root `0755`; compares supplied credentials with that record |
| `files/ground-truth.json` | `/usr/share/iotbench/hardcoded-user-passwords/ground-truth.json`, `0644`; account, password, consumer, exact label and CWE |
| `files/NOTICE` | `/usr/share/iotbench/hardcoded-user-passwords/NOTICE`, `0644`; exact warning and synthetic scope |
| `files/test-guest.sh` | `/usr/share/iotbench/hardcoded-user-passwords/test-guest.sh`, `0644`; explicitly invoked local regression |
| `files/LICENSE` | Existing repository MIT license convention |

`meta-iotbench/recipes-images/iotbench-hardcoded-user-passwords.inc` fails
image generation if the credential bytes differ from the source or if the
database/helper ownership and modes change. It appends NOTICE to `/etc/motd`;
the helper itself also prints the exact warning. The database has normal
root-only permissions, and the helper has no SUID/SGID or sudo grant. Those
permissions limit live file access, but an analyzer can extract the plaintext
from the ext4 firmware without authenticating or booting it. The embedded
credential remains recoverable from every distributed copy.

Detection must correlate **a real synthetic account record, a fixed embedded
password, deterministic image installation, and the helper's authentication
comparison**. A random string containing `password`, `passwd`, `credential` or
`secret` is insufficient by itself. Metadata is an annotation of the expected
finding, not a substitute for tracing the actual account-to-consumer relationship.

This differs from generic vulnerable Java/JAR applications and generic vulnerable
C binaries: the package has neither and installs an actual firmware account
configuration and its local shell authentication component. It differs from
unused password-looking sample strings because the stored password controls
authentication. It contains no real leaked credentials: both account and password
are clearly fake and exclusively dedicated to this fixture. Ordinary
`/etc/passwd` entries with no hardcoded password do not establish this scenario,
and neither do password hashes or authentication artifacts lacking a tie to a
deterministic hardcoded account credential. Generic weak-password examples
where a password is supplied externally are also different: here the firmware
itself ships the fixed credential, regardless of a caller's submitted input.

### Shared local build and testing

Run host commands from the repository root. The default machine is `qemuarm64`;
`YOCTO_MACHINE` selects the existing `qemuarm`, `qemux86-64`, `qemux86` or
`qemumips` alternatives. Use the same selector for building and booting.
`scripts/build-all.sh` discovers these eleven image recipes automatically.
To parse and resolve one target without building, use:

~~~bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe798-hardcoded-user-passwords'
~~~

Build all eleven:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe798-hardcoded-user-passwords.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

Each export contains the compressed ext4 rootfs and kernel. Per-device paths
and commands follow below. Log into a manually booted guest through its serial
console using the common `root` / `routeradmin` development login, then run:

~~~bash
cat /etc/iotbench/hardcoded-user-passwords/accounts.conf
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
printf '%s\n' 'fixture-password-wrong' | iotbench-fixture-auth fixtureuser
~~~

Expected: the fixed account record; then the success marker with status zero;
then `FIXTURE_AUTH_REJECTED` with status 1. Authentication needs only the
local files and stdin; no HTTP, SSH, Telnet, FTP, MQTT or Modbus client is used.

The installed `test-guest.sh` verifies deterministic account content, device
identity, normal permissions, repeated success, wrong account/password, missing
or empty input, extra arguments and shell-shaped data rejection. In the
**disposable test snapshot only**, it temporarily replaces the stored password:
the original password must fail and the replacement must succeed. It then checks
that missing/empty credential storage fails closed and restores the original
account record. This is evidence that the helper uses the installed credential;
the temporary test edit is not firmware provisioning or a production fix.
Expected: four `PASS` lines and status zero.

`scripts/test-hardcoded-user-passwords.py --image <path>` inspects an ext4 or
ext4.zst image with `debugfs`, checking credential bytes, the exact installed
consumer/test, ownership, permissions, metadata, device identity and the warning.
It does not mount or execute the firmware. Run it on the host with Python 3,
`zstd` and `debugfs`, or use the existing builder container as in the per-device
commands. Expected: two `PASS` lines and status zero.

The same host runner uses `--device <device>` or `--all` to boot disposable
QEMU snapshots and run the guest regression over the serial console. Run it
separately from a manually running QEMU instance. QEMU and `zstd` must be
installed on the host. For Apple Silicon acceleration and unused host ports:

~~~bash
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-hardcoded-user-passwords.py --all
~~~

Console logs are saved in each exported firmware directory as
`validation-console.log`. These host-port settings only support the existing
device profiles; the regression uses no network authentication.

### Safe remediation

For a corrected firmware variant, remove the embedded shared password and enroll
a unique account credential separately for each installation. Keep a salted
password hash in an access-controlled credential store outside the distributable
firmware and support rotation. Merely changing the shared literal, embedding its
hash, hiding it or retaining root-only permissions does not remove deterministic
credential reuse. Verify that the published fixture password no longer succeeds,
that an enrolled credential does succeed locally, and that it fails on another
installation. Rebuild source changes for a lasting variant; QEMU snapshots
discard temporary edits. The known-positive fixture regression must fail its
hardcoded-credential assertion against a properly corrected variant.


### Completed validation

On 2026-10-07, all eleven `qemuarm64` fixtures built and exported successfully
after BitBake parsing and router dependency dry-run validation. Offline
`debugfs` inspection of every compressed ext4 export confirmed the exact
`fixtureuser:fixture-password-123` account record, installed authentication
consumer and guest test, root-owned `0600` database, ordinary `0755` helper,
device identity, metadata and required warning. Account and helper bytes were
identical across all device images.

All eleven images booted in disposable QEMU snapshots using HVF and the host
CPU. Each passed all four guest regression groups, including repeated use of
the fixed password, rejection checks, temporary password replacement proving
credential consumption, and missing/empty database failure with restoration.
The tests used the serial console; authentication required no networking.
Every image manifest contained exactly one vulnerability package,
`cwe798-hardcoded-user-passwords`.

The [local validation report](../deploy-images/hardcoded-user-passwords-qemuarm64-validation.txt)
contains results and rootfs/kernel/helper SHA-256 checksums. Each firmware
export also contains `validation-console.log` and `rootfs.manifest`. Full
build and parse logs are saved as
`deploy-images/hardcoded-user-passwords-qemuarm64-build.log` and
`deploy-images/hardcoded-user-passwords-qemuarm64-parse.log`.
Other supported architectures were not built or boot-tested in this run.
The CWE-798 finding is expected ground truth; validation used actual builds,
filesystem inspection and local authentication, without running an external
firmware-analysis engine.

### doorlock-cwe798-hardcoded-user-passwords

Simulated device: **access-control door lock**, using the existing
`meta-iotbench/recipes-devices/doorlock/` profile. Firmware directory:
`deploy-images/doorlock-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-doorlock-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/doorlock-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-doorlock-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=doorlock-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=doorlock-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh doorlock
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/doorlock-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-doorlock-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device doorlock
~~~


### envsensor-cwe798-hardcoded-user-passwords

Simulated device: **environmental sensor**, using the existing
`meta-iotbench/recipes-devices/envsensor/` profile. Firmware directory:
`deploy-images/envsensor-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-envsensor-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/envsensor-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-envsensor-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=envsensor-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=envsensor-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh envsensor
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/envsensor-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-envsensor-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device envsensor
~~~


### healthmonitor-cwe798-hardcoded-user-passwords

Simulated device: **health monitor**, using the existing
`meta-iotbench/recipes-devices/healthmonitor/` profile. Firmware directory:
`deploy-images/healthmonitor-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/healthmonitor-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-healthmonitor-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh healthmonitor
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/healthmonitor-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-healthmonitor-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device healthmonitor
~~~


### ipcamera-cwe798-hardcoded-user-passwords

Simulated device: **surveillance IP camera**, using the existing
`meta-iotbench/recipes-devices/ipcamera/` profile. Firmware directory:
`deploy-images/ipcamera-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/ipcamera-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-ipcamera-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=ipcamera-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh ipcamera
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/ipcamera-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-ipcamera-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device ipcamera
~~~


### plc-cwe798-hardcoded-user-passwords

Simulated device: **industrial PLC gateway (OT)**, using the existing
`meta-iotbench/recipes-devices/plc/` profile. Firmware directory:
`deploy-images/plc-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-plc-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/plc-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-plc-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=plc-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=plc-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh plc
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/plc-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-plc-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device plc
~~~


### router-cwe798-hardcoded-user-passwords

Simulated device: **network gateway/router**, using the existing
`meta-iotbench/recipes-devices/router/` profile. Firmware directory:
`deploy-images/router-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-router-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/router-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-router-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=router-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=router-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh router
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/router-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-router-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device router
~~~


### smartbulb-cwe798-hardcoded-user-passwords

Simulated device: **lighting smart bulb**, using the existing
`meta-iotbench/recipes-devices/smartbulb/` profile. Firmware directory:
`deploy-images/smartbulb-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/smartbulb-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smartbulb-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=smartbulb-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh smartbulb
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/smartbulb-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smartbulb-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device smartbulb
~~~


### smarthub-cwe798-hardcoded-user-passwords

Simulated device: **controller/smart hub**, using the existing
`meta-iotbench/recipes-devices/smarthub/` profile. Firmware directory:
`deploy-images/smarthub-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smarthub-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/smarthub-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smarthub-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smarthub-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=smarthub-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh smarthub
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/smarthub-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smarthub-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device smarthub
~~~


### smartplug-cwe798-hardcoded-user-passwords

Simulated device: **energy-management smart plug**, using the existing
`meta-iotbench/recipes-devices/smartplug/` profile. Firmware directory:
`deploy-images/smartplug-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartplug-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/smartplug-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smartplug-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartplug-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=smartplug-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh smartplug
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/smartplug-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smartplug-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device smartplug
~~~


### smartspeaker-cwe798-hardcoded-user-passwords

Simulated device: **audio/voice-assistant smart speaker**, using the existing
`meta-iotbench/recipes-devices/smartspeaker/` profile. Firmware directory:
`deploy-images/smartspeaker-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/smartspeaker-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smartspeaker-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh smartspeaker
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/smartspeaker-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smartspeaker-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device smartspeaker
~~~


### thermostat-cwe798-hardcoded-user-passwords

Simulated device: **climate-control thermostat**, using the existing
`meta-iotbench/recipes-devices/thermostat/` profile. Firmware directory:
`deploy-images/thermostat-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-thermostat-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/thermostat-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-thermostat-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=thermostat-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=thermostat-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh thermostat
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/thermostat-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-thermostat-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device thermostat
~~~


## CoAP Server Communicating with Vulnerable Internal Files (CWE-862)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario, authorization boundary and ground truth

The eleven `<device>-cwe862-coap-internal-files` images reuse the existing
device profiles, common Yocto image, pinned layers, systemd startup conventions,
architecture selector and build/export scripts. Each installs exactly one
vulnerability package, `cwe862-coap-internal-files`. The repository had no
CoAP-specific fixture; the existing `meta-networking` layer already supplies
the pinned `libcoap` recipe used by this firmware-integrated daemon.

The expected ground-truth label is **CoAP server communicating with vulnerable
internal files**. The modeled vulnerability is specifically **unsafe exposure
of synthetic internal firmware files through a CoAP server because the CoAP
resource lacks adequate access control**. We classify the absent resource
authorization as [CWE-862 — Missing Authorization](https://cwe.mitre.org/data/definitions/862.html);
disclosure of internal information is its consequence, not a second fixture
vulnerability. There is no credential or authentication-bypass chain.

The attacker position is a CoAP client that can reach guest UDP port `5683`.
The normal host runner forwards it only through `127.0.0.1`. A request without
any identity, credential, session or maintenance role receives the internal
file bytes. CoAP message tokens correlate requests and responses; they do not
authenticate the client.

### Resource-to-file mappings and intended privacy

All application file access is restricted to this predefined mapping:

| CoAP GET resource | Fixed internal firmware file | Synthetic contents / exposure signal |
| --- | --- | --- |
| `/device/config` | `/usr/share/iotbench/coap-internal-files/internal/device.conf` | Device class, fake asset reference, calibration profile and diagnostic mode; `COAP_INTERNAL_CONFIG_EXPOSED` |
| `/maintenance/info` | `/usr/share/iotbench/coap-internal-files/internal/maintenance.dat` | Fake maintenance reference, service window and self-test state; `COAP_INTERNAL_MAINTENANCE_EXPOSED` |

Both files are shipped in the firmware, marked `fixture_scope=internal-maintenance-only`,
and contain the exact fixture warning. They contain no host data, real credentials,
API keys, tokens, personal data or external-system information. They are internal
maintenance/configuration artifacts by fixture policy, rather than intentionally
public telemetry. Normal Unix permissions restrict their direct access to root
and the daemon's service group, but the protocol handler omits the maintenance
authorization boundary before returning them to any reachable client.

The source `files/device.conf` has an `@DEVICE@` placeholder. The image-only
`iotbench-coap-internal-files.inc` replaces it with the profile's existing
`IOTBENCH_DEVICE` at build time, checks ownership/permissions and appends NOTICE
to `/etc/motd`. This creates deterministic per-device synthetic configuration.
`maintenance.dat` and daemon code are identical across the eleven images.
There is no runtime file generation or mutation by the service.

### Server implementation, startup and static data flow

The source directory is
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`. Its recipe uses local
`file://` sources and standard `${CC}`, `${CFLAGS}` and `${LDFLAGS}` with
`pkg-config --cflags --libs libcoap-3-openssl`. The existing pinned
`libcoap_4.3.5b.bb` provides RFC 7252 CoAP framing, URI matching and responses;
the daemon creates only an IPv4 UDP endpoint. No DTLS/TCP service, external
client connection, scan, shell or command execution is configured. See
[RFC 7252](https://www.rfc-editor.org/rfc/rfc7252.html) and the
[libcoap handler API](https://libcoap.net/doc/reference/4.3.5/man_coap_handler.html).

The static data flow is:

~~~text
CoAP GET /device/config or /maintenance/info
  -> libcoap matches an explicitly registered resource
  -> get_internal_file(resource)
  -> resource userdata selects a constant filename from resources[]
  -> openat(pre-opened fixed internal directory, constant filename, O_RDONLY)
  -> fstat and bounded read into content[]
  -> coap_add_data(response, byte_count, content)
  -> libcoap sends 2.05 Content with the internal file bytes
~~~

The `resources[]` table in `iotbench-coap-internal-files.c` fixes both URI and
filename; `coap_resource_set_userdata` ties each resource to its mapping.
`coap_register_request_handler(..., COAP_REQUEST_GET, get_internal_file)`
registers the only application operation. `main` opens the fixed internal
directory once. Inside `get_internal_file`, `openat` opens the mapped file and
`read` supplies the bytes later passed to `coap_add_data`. The handler sets
`COAP_RESPONSE_CODE_CONTENT`; libcoap transmits the response when it returns.
The installed source annotation `handler.c` accompanies the executable to make
this short flow directly available to static-analysis tools.

The intentionally missing check is **authorization of the requesting client
for internal maintenance-file access before `openat`/`read`**. Checking the
file's type or the URI syntax is not an authorization check. A static analyzer
should correlate the registered CoAP handlers, constant internal files,
read-to-response data flow and absence of that access decision.

| Component | Firmware path / permissions |
| --- | --- |
| Daemon | `/usr/bin/iotbench-coap-internal-files`, root:root `0755`, no SUID/SGID |
| Startup | `/usr/lib/systemd/system/iotbench-coap-internal-files.service`; enabled for `multi-user.target` |
| Service identity | `coapfixture`, UID/GID `992:992`, locked password and `/bin/false` shell |
| Internal directory | `/usr/share/iotbench/coap-internal-files/internal/`, root:coapfixture `0750` |
| Internal files | `device.conf` and `maintenance.dat`, root:coapfixture `0640` |
| Analysis source | `/usr/share/iotbench/coap-internal-files/handler.c`, `0644` |
| Ground truth | `/usr/share/iotbench/coap-internal-files/ground-truth.json`, `0644` |
| Warning | `/usr/share/iotbench/coap-internal-files/NOTICE` and `/etc/motd` |

Yocto's existing `useradd` and `systemd` classes install the locked service
identity and enable startup. The unit uses `Type=simple`,
`ExecStart=/usr/bin/iotbench-coap-internal-files`, `User=coapfixture`,
`Group=coapfixture` and `After=network.target`. It retains strict filesystem
protection, no new privileges, an empty capability set, private temporary/device
namespaces and restricted socket families. The daemon prints the exact warning
when starting. UDP port 5683 needs no privileged capability; no sudo rule or
OS login credential is introduced.

### Read-only scope and distinctions

The daemon rejects query strings and request bodies with `4.00 Bad Request`.
Unknown resource URIs return `4.04 Not Found`; unregistered write methods such
as POST, PUT and DELETE return `4.05 Method Not Allowed`. Request URIs, query
strings and payloads never become filenames or path fragments. The two fixed
files are opened with `O_NOFOLLOW` and `O_NONBLOCK`, checked as regular files,
and read with a maximum of 512 bytes. Missing files, symlinks, empty files and
oversized/non-regular files fail with `5.00 Internal Server Error`.
There is no application access to other files or any write operation. Libcoap's
standard resource discovery may list the registered URIs; it does not expose
additional internal files.

This fixture differs from generic vulnerable Java/JAR applications: none is
installed. It differs from a generic vulnerable C binary unrelated to firmware:
this executable is a real systemd-started CoAP service linked to actual
image-installed files. It differs from ordinary CoAP serving intentionally
public information: these files are explicitly internal-maintenance-only.
It differs from a generic network service because the request/resource/response
is CoAP, backed by libcoap rather than a custom line protocol.

It differs from Path Traversal and arbitrary file-read examples: clients select
only registered resources, never filesystem paths, and cannot escape the
predefined mapping. It differs from command-execution vulnerabilities because
the handler performs only bounded reads and response construction. It differs
from hardcoded-credential fixtures because this service contains no login
password or shared authorization secret. It also differs from ordinary internal
files never reachable through a protocol handler: here a CoAP GET actually
returns those file bytes.

**A CoAP server merely existing is not sufficient. An internal file merely
existing is not sufficient.** The finding requires a demonstrable relationship:
**a CoAP-accessible resource exposes information originating from a predefined
internal firmware file without appropriate access restrictions**. A resource
name, marker string or metadata label alone does not establish the vulnerability.

### Local build and manual testing

Run host commands from the repository root. Validate the layer and one graph:

~~~bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe862-coap-internal-files'
~~~

Build all eleven using the normal exporter:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe862-coap-internal-files.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

The default is `qemuarm64`. The existing `YOCTO_MACHINE` selector also supports
`qemuarm`, `qemux86-64`, `qemux86` and `qemumips`; use the same selector for
build and boot. `scripts/build-all.sh` discovers all these recipes automatically.
Outputs go to `deploy-images/<device>-cwe862-coap-internal-files/<machine>/`.

Boot a selected image with its per-device command below. On Apple Silicon add
`QEMU_ACCEL=hvf QEMU_CPU=host`. The host forwards
`127.0.0.1:5683/udp` to guest `5683/udp`; `QEMU_COAP_PORT` changes only the
host UDP port. Existing HTTP/MQTT/Modbus profile forwarding is retained.
For a complete manual router example on Apple Silicon, run this on the host
from the repository root (skip rebuilding if the image is already exported):

~~~bash
FIRMWARE=router-cwe862-coap-internal-files docker compose run --rm yocto
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 QEMU_COAP_PORT=5683 \
  FIRMWARE=router-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Wait until the QEMU console shows `login:`. The startup output must include
`CoAP: coap://127.0.0.1:5683`. No guest login is needed for a CoAP request.
Use a second host terminal for these manual reads:

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` followed by the exact internal file content and the
corresponding `COAP_INTERNAL_CONFIG_EXPOSED` or
`COAP_INTERNAL_MAINTENANCE_EXPOSED` line. No credentials or role are supplied.
These are CoAP/UDP endpoints; an HTTP browser or ordinary HTTP curl request does
not exercise them. If using host UDP port 15683, add `--port 15683` to every
client command. The standard-library client only contacts host loopback and
does not discover or scan other machines.

From the guest's root serial console (existing `root` / `routeradmin`
development login), inspect the source of those same bytes and service:

~~~bash
systemctl status iotbench-coap-internal-files.service --no-pager
cat /usr/share/iotbench/coap-internal-files/internal/device.conf
cat /usr/share/iotbench/coap-internal-files/internal/maintenance.dat
~~~

Compare the file contents with the CoAP response. This inspection is evidence
of file origin; root login is not required by the CoAP request.

#### Manual file-origin check in a disposable snapshot

After logging into the guest serial console, append one synthetic line
**inside the guest**:

~~~bash
printf '%s\n' 'fixture_probe=manual-test' >> /usr/share/iotbench/coap-internal-files/internal/device.conf
~~~

Then repeat the request **from the host terminal**:

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
~~~

The `2.05 Content` response must now include `fixture_probe=manual-test`.
This proves that the response originates from the current internal file rather
than an unused string or fixed response literal. Quit QEMU with **Ctrl-A**, then
**X**; the normal disposable snapshot discards this test edit.

#### Connection refused: match the forwarded UDP port

`ConnectionRefusedError: [Errno 61] Connection refused` can occur when the
client uses a host UDP port that QEMU is not forwarding. Check the
`CoAP: coap://127.0.0.1:<port>` line printed when QEMU starts.

For example, if QEMU was started without `QEMU_COAP_PORT`, its default host
port is **5683**, so the working commands are:

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Using `--port 15683` against that instance will not reach the server. To use
15683, first quit QEMU and restart it with `QEMU_COAP_PORT=15683`, then use
`--port 15683` in every host client command. Changing a shell variable after
QEMU has started does not change the existing forwarding.

If the port matches but the server still does not respond, inspect
`systemctl status iotbench-coap-internal-files.service --no-pager` inside the
guest and confirm that the selected firmware is `router-cwe862-coap-internal-files`
(or another device's matching CoAP fixture).

### Automated local verification and remediation

Against an already running fixture, use the per-device `--device` command.
Expected: two `PASS` lines. It checks exact unauthenticated file exposure with
CON and NON messages, repeated GETs, correct tokens/message IDs/Content-Format,
and rejection of unknown/path-shaped URIs, queries, request bodies and write
methods without changing either file.

Use `--boot <device>` or `--all` separately from manual QEMU to let the runner
boot/test/close disposable snapshots. Expected: three `PASS` lines per image.
It also checks the enabled service, identity, warning and file metadata, then
temporarily changes only the synthetic internal configuration file inside the
disposable guest. The changed content must appear over CoAP, proving the actual
file-read-to-response relationship. Missing, symlink and oversized internal
files must fail closed; the original bytes are restored. No host file is
modified or exposed.

~~~bash
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 QEMU_COAP_PORT=15683 \
  python3 scripts/test-coap-internal-files.py --all
~~~

Offline `--image` verification reads ext4 or ext4.zst via `debugfs` without
mounting or executing it. It checks the two synthetic files, actual ELF URI/file
mappings, installed handler source, locked unprivileged account, service/enable
link, permissions, ground truth and warning. Use the builder commands below, or
host Python 3 with `zstd` and `debugfs`. Expected: two `PASS` lines.
Console evidence is saved alongside each exported image as `validation-console.log`.

Safe remediation is to remove internal-file resources from the externally
reachable CoAP interface, or establish client identity and explicitly authorize
the maintenance role before opening the files. A secure transport such as DTLS
can support client authentication, but transport encryption alone does not decide
who is authorized to read each resource. Keep the constant mapping, unprivileged
identity, bounded reads and normal filesystem permissions. A corrected variant
should reject anonymous GETs, permit only an authorized maintenance client and
continue rejecting unknown resources and writes. The known-positive exposure
test must then fail its unrestricted-content assertion. Apply source changes
and rebuild for a lasting fix; normal QEMU snapshots discard test edits.


### Completed validation

On 2026-10-07, all eleven `qemuarm64` fixtures built and exported successfully
after BitBake parsing and a router dependency dry run. Offline `debugfs`
inspection of every compressed ext4 export confirmed the two exact synthetic
files and device class, fixed URI/file mappings in the ELF, matching installed
handler source, locked UID/GID 992 daemon account, enabled systemd unit,
`0640` internal files in a `0750` directory, ground truth and required warning.
The daemon ELF and maintenance file were identical across all device images.
Each package manifest contained exactly one vulnerability package,
`cwe862-coap-internal-files`.

All eleven images booted in disposable QEMU snapshots using HVF and the host
CPU. Every image passed unauthenticated CON/NON GET checks with exact file
bytes, repeated requests and the normal rejection controls. A temporary change
to the actual internal synthetic configuration appeared in the CoAP response,
demonstrating file origin. Missing, symlink and oversized files were rejected;
the original content was restored. All CoAP requests targeted host loopback
UDP 15683, forwarded to guest UDP 5683.

The [local validation report](../deploy-images/coap-internal-files-qemuarm64-validation.txt)
records results, source/file-origin evidence and rootfs/kernel/daemon/file
SHA-256 checksums. Every export includes `rootfs.manifest`,
`validation-console.log` and `validation-protocol.log`. Build logs are saved
as `deploy-images/coap-internal-files-qemuarm64-build.log` and
`deploy-images/coap-internal-files-qemuarm64-parse-and-initial-build.log`.
Other supported architectures were not built or boot-tested in this run.
No external firmware-analysis engine was run; static findings remain expected
ground truth corroborated by real firmware files and protocol behavior.

### doorlock-cwe862-coap-internal-files

Simulated device: **access-control door lock**, reusing
`meta-iotbench/recipes-devices/doorlock/`. Firmware directory:
`deploy-images/doorlock-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-doorlock-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/doorlock-cwe862-coap-internal-files/qemuarm64/iotbench-doorlock-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 992.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=doorlock`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=doorlock-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=doorlock-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=doorlock` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device doorlock`.
Alternatively, use `--boot doorlock` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/doorlock-cwe862-coap-internal-files/qemuarm64/iotbench-doorlock-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### envsensor-cwe862-coap-internal-files

Simulated device: **environmental sensor**, reusing
`meta-iotbench/recipes-devices/envsensor/`. Firmware directory:
`deploy-images/envsensor-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-envsensor-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/envsensor-cwe862-coap-internal-files/qemuarm64/iotbench-envsensor-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 992.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=envsensor`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=envsensor-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=envsensor-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=envsensor` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device envsensor`.
Alternatively, use `--boot envsensor` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/envsensor-cwe862-coap-internal-files/qemuarm64/iotbench-envsensor-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### healthmonitor-cwe862-coap-internal-files

Simulated device: **health monitor**, reusing
`meta-iotbench/recipes-devices/healthmonitor/`. Firmware directory:
`deploy-images/healthmonitor-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/healthmonitor-cwe862-coap-internal-files/qemuarm64/iotbench-healthmonitor-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 992.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=healthmonitor`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=healthmonitor` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device healthmonitor`.
Alternatively, use `--boot healthmonitor` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/healthmonitor-cwe862-coap-internal-files/qemuarm64/iotbench-healthmonitor-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### ipcamera-cwe862-coap-internal-files

Simulated device: **surveillance IP camera**, reusing
`meta-iotbench/recipes-devices/ipcamera/`. Firmware directory:
`deploy-images/ipcamera-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/ipcamera-cwe862-coap-internal-files/qemuarm64/iotbench-ipcamera-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 992.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=ipcamera`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=ipcamera-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=ipcamera` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device ipcamera`.
Alternatively, use `--boot ipcamera` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/ipcamera-cwe862-coap-internal-files/qemuarm64/iotbench-ipcamera-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### plc-cwe862-coap-internal-files

Simulated device: **industrial PLC gateway (OT)**, reusing
`meta-iotbench/recipes-devices/plc/`. Firmware directory:
`deploy-images/plc-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-plc-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/plc-cwe862-coap-internal-files/qemuarm64/iotbench-plc-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 992.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=plc`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=plc-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=plc-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=plc` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device plc`.
Alternatively, use `--boot plc` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/plc-cwe862-coap-internal-files/qemuarm64/iotbench-plc-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### router-cwe862-coap-internal-files

Simulated device: **network gateway/router**, reusing
`meta-iotbench/recipes-devices/router/`. Firmware directory:
`deploy-images/router-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-router-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/router-cwe862-coap-internal-files/qemuarm64/iotbench-router-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 992.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=router`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=router-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=router-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=router` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device router`.
Alternatively, use `--boot router` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/router-cwe862-coap-internal-files/qemuarm64/iotbench-router-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### smartbulb-cwe862-coap-internal-files

Simulated device: **lighting smart bulb**, reusing
`meta-iotbench/recipes-devices/smartbulb/`. Firmware directory:
`deploy-images/smartbulb-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/smartbulb-cwe862-coap-internal-files/qemuarm64/iotbench-smartbulb-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 992.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=smartbulb`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=smartbulb-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=smartbulb` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device smartbulb`.
Alternatively, use `--boot smartbulb` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/smartbulb-cwe862-coap-internal-files/qemuarm64/iotbench-smartbulb-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### smarthub-cwe862-coap-internal-files

Simulated device: **controller/smart hub**, reusing
`meta-iotbench/recipes-devices/smarthub/`. Firmware directory:
`deploy-images/smarthub-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smarthub-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/smarthub-cwe862-coap-internal-files/qemuarm64/iotbench-smarthub-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 992.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=smarthub`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smarthub-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=smarthub-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=smarthub` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device smarthub`.
Alternatively, use `--boot smarthub` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/smarthub-cwe862-coap-internal-files/qemuarm64/iotbench-smarthub-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### smartplug-cwe862-coap-internal-files

Simulated device: **energy-management smart plug**, reusing
`meta-iotbench/recipes-devices/smartplug/`. Firmware directory:
`deploy-images/smartplug-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartplug-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/smartplug-cwe862-coap-internal-files/qemuarm64/iotbench-smartplug-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 992.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=smartplug`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartplug-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=smartplug-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=smartplug` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device smartplug`.
Alternatively, use `--boot smartplug` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/smartplug-cwe862-coap-internal-files/qemuarm64/iotbench-smartplug-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### smartspeaker-cwe862-coap-internal-files

Simulated device: **audio/voice-assistant smart speaker**, reusing
`meta-iotbench/recipes-devices/smartspeaker/`. Firmware directory:
`deploy-images/smartspeaker-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/smartspeaker-cwe862-coap-internal-files/qemuarm64/iotbench-smartspeaker-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 992.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=smartspeaker`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=smartspeaker` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device smartspeaker`.
Alternatively, use `--boot smartspeaker` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/smartspeaker-cwe862-coap-internal-files/qemuarm64/iotbench-smartspeaker-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### thermostat-cwe862-coap-internal-files

Simulated device: **climate-control thermostat**, reusing
`meta-iotbench/recipes-devices/thermostat/`. Firmware directory:
`deploy-images/thermostat-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-thermostat-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/thermostat-cwe862-coap-internal-files/qemuarm64/iotbench-thermostat-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 992.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=thermostat`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=thermostat-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=thermostat-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=thermostat` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device thermostat`.
Alternatively, use `--boot thermostat` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/thermostat-cwe862-coap-internal-files/qemuarm64/iotbench-thermostat-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~

## MQTT Server Communicating with Vulnerable Internal Files (CWE-862)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario and authorization boundary

Every implemented device profile has a separate
`<device>-cwe862-mqtt-internal-files` image. These images reuse the existing
Yocto image/device includes, pinned Mosquitto recipe, systemd startup,
peripheral simulator, architecture selector and build/export scripts. Each
installs exactly one vulnerability package, `cwe862-mqtt-internal-files`.
The existing MQTT architecture remains a local Mosquitto broker with firmware
publishers; the router, camera and PLC receive that same broker as a fixture
component alongside their HTTP or Modbus service.

Expected ground-truth label: **MQTT Server Communicating with Vulnerable
Internal Files**. Expected weakness: **CWE-862 — Missing Authorization**.
The consequence is unsafe exposure of synthetic internal firmware information.
The finding requires all four elements: **internal firmware file + MQTT
publisher + MQTT-accessible topic + insufficient topic access restriction**.
An analyzer must establish their relationship; a broker, file, topic name or
exposure marker alone is insufficient.

A client reaching guest TCP `1883` connects anonymously and subscribes to
`device/config` or `maintenance/info`. The broker's public ACL explicitly
grants every anonymous subscriber read access to these internal-maintenance-only
topics. It never requires a maintenance identity or role. The defect is that
specific read grant, rather than a credential bypass or another vulnerability.
Ordinary public peripheral telemetry remains under `iotbench/<device>/#`.
Public MQTT writes, including writes to the internal topics, are denied.

### Fixed internal files, topics and data flow

| Vulnerable MQTT topic | Fixed firmware file | Synthetic contents |
| --- | --- | --- |
| `device/config` | `/usr/share/iotbench/mqtt-internal-files/internal/device.conf` | Device class, fake asset reference, synthetic calibration profile and diagnostic mode; `MQTT_INTERNAL_CONFIG_EXPOSED` |
| `maintenance/info` | `/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat` | Fake maintenance reference, fixture service window and synthetic self-test state; `MQTT_INTERNAL_MAINTENANCE_EXPOSED` |

Both files ship inside the firmware, contain the exact warning above, and are
marked `fixture_scope=internal-maintenance-only`. Their contents are authored
fixture data, with no host data, real credentials, API keys, tokens,
certificates, personal information or external-system data. The config's
`@DEVICE@` placeholder becomes the selected device class during the image's
rootfs postprocessing; the maintenance file is identical across devices.
These are private maintenance artifacts by fixture policy. Publishing them to
arbitrary subscribers crosses that intended boundary, even though all values
are synthetic. Unix permissions are root:mqttfixture `0640` inside a `0750`
directory, so they are not ordinary world-readable firmware files.

The concrete vulnerable flow is:

~~~text
fixed internal synthetic device.conf / maintenance.dat
  -> mappings[] supplies a constant filename and corresponding topic
  -> read_internal(): openat(fixed directory, constant filename), fstat, read
  -> publish_files(): mosquitto_publish(topic, exact file bytes, QoS 1, retained)
  -> local Mosquitto receives the publication on guest-loopback TCP 1884
  -> public listener TCP 1883 applies iotbench-public.acl
  -> anonymous topic read is granted without maintenance authorization
  -> MQTT subscriber receives the internal file contents
~~~

The C source `files/iotbench-mqtt-internal-files.c` in
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/` contains the static
`mappings[]` table. `main()` opens only the fixed internal directory and connects
only to `127.0.0.1:1884` in the guest. `read_internal()` reads one of the two
constant filenames; `publish_files()` passes those bytes directly to
`mosquitto_publish()`. The publisher has no subscriptions or message callback,
so MQTT messages cannot select filenames, paths, commands or operations.
It publishes both files every five seconds, with retained QoS 1 messages for
new subscribers. Retention is in broker memory, with disk persistence disabled.

Expected static-analysis finding: join the image-installed private files,
constant mappings, `openat`/`read` to `mosquitto_publish` data flow, active broker
configuration and anonymous `topic read` grants. Identify the absent
maintenance-role authorization before disclosure. Source annotation
`publisher.c` and `ground-truth.json` are installed alongside the real ELF,
configuration, ACLs and synthetic files to support firmware analysis.
No external analysis engine is required to inspect this short chain.

### Broker, startup and ACL configuration

| Component | Firmware path / behavior |
| --- | --- |
| Local broker | `/usr/sbin/mosquitto`, from the existing pinned `mosquitto_2.1.2.bb` recipe |
| Active broker config | `/etc/mosquitto/iotbench.conf`; public listener `0.0.0.0:1883`, private publishing listener `127.0.0.1:1884`, `per_listener_settings true`, `allow_anonymous true`, `persistence false` |
| Public ACL | `/etc/mosquitto/iotbench-public.acl`; ordinary `topic read iotbench/#` plus **intentionally unsafe** `topic read device/config` and `topic read maintenance/info`; all writes/other reads denied by default |
| Publishing ACL | `/etc/mosquitto/iotbench-publish.acl`; write-only access to `iotbench/#`, `device/config`, `maintenance/info`; no reads or other writes |
| Broker startup | `/usr/lib/systemd/system/mosquitto.service.d/10-iotbench-listener.conf`; replaces `ExecStart` with `/usr/sbin/mosquitto -c /etc/mosquitto/iotbench.conf` and uses the existing `Type=simple` convention |
| Fixture publisher | `/usr/bin/iotbench-mqtt-internal-files`; ordinary root-owned `0755`, no SUID/SGID |
| Publisher startup | `/usr/lib/systemd/system/iotbench-mqtt-internal-files.service`; enabled at `multi-user.target`, `After`/`Requires`/`PartOf=mosquitto.service`, restart on failure |
| Publisher identity | `mqttfixture`, locked UID/GID `991:991`, `/bin/false`, no OS login credential |
| Native telemetry integration | `/usr/lib/systemd/system/iotbench-mqtt.service.d/10-fixture-publisher.conf`; sets `MQTT_BROKER=127.0.0.1 MQTT_PORT=1884` for existing MQTT profiles |
| Private files | `/usr/share/iotbench/mqtt-internal-files/internal/{device.conf,maintenance.dat}`, root:991 `0640`, parent `0750` |
| Analysis annotations | `/usr/share/iotbench/mqtt-internal-files/{publisher.c,ground-truth.json,NOTICE}`, `0644` |
| Firmware warning | `NOTICE`, each internal file, `/etc/motd`, publisher startup log and image recipe description |

Mosquitto's [ACL documentation](https://mosquitto.org/man/mosquitto-conf-5.html)
defines the initial `topic` rules as applying to anonymous clients. Its
[client API](https://mosquitto.org/api/files/mosquitto-h.html) supplies the
publisher's connect/loop/publish operations. No different broker, framework or
custom MQTT protocol implementation replaces the repository architecture.
The recipe compiles local C sources with `${CC}`, `${CFLAGS}`, `${LDFLAGS}`
and `-lmosquitto`, using the existing recipe dependency. No publisher or broker
invokes a shell or package manager.

The public listener is reachable only through host-loopback forwarding in
`scripts/run-qemu.sh`. Port `1884` is bound to **guest loopback**, never forwarded,
and has no external broker bridge. The fixed publisher client ID is only a
protocol correlation label; ACLs do not trust it as an authentication identity.
No MQTT username, password or shared authorization secret is introduced.
The existing serial-console lab login belongs to the common harness and is
unnecessary for anonymous MQTT exposure.

The native telemetry script accepts `MQTT_PORT` with its existing `1883`
default. Only these fixtures set it to `1884`, allowing the shared publisher to
continue serving normal peripheral telemetry through the same broker while the
public listener remains read-only. Non-MQTT profiles retain their camera/HTTP
or Modbus services; the telemetry drop-in is inert when that unit is absent.

The fixture publisher runs unprivileged, with strict filesystem protection,
no new privileges, an empty capability set, private temporary/device namespaces,
and loopback-only network policy. It opens the fixed directory and filenames
with `O_NOFOLLOW`; regular-file checks and bounded reads limit each payload to
1024 bytes. Missing, empty, symlink, non-regular or oversized files clear the
corresponding retained message rather than expose stale data. Invalid files
cannot redirect the read or block on a FIFO. Valid contents are read again on
the next publishing cycle. A broker restart restarts the fixture publisher and
repopulates both retained topics. There is no application filesystem write.

### Scope and distinctions

These are firmware-integrated MQTT fixtures, rather than generic Java/JAR apps
or unrelated vulnerable C executables: Yocto installs the files, ELF, broker,
ACLs and enabled services together in each device image. They differ from an
ordinary MQTT broker because an actual publisher reads private firmware files
and sends their contents to incorrectly authorized topics. They differ from
public telemetry because both files are explicitly internal-maintenance-only.
They differ from ordinary private files never exposed through MQTT because the
file bytes are observable over a real MQTT subscription.

They differ from Path Traversal and arbitrary file-read examples: all paths are
implementation constants and the publisher accepts no client input. Unknown or
path-like topics do not cause file access. They differ from command-execution
vulnerabilities: no received command is interpreted, no shell is launched and
no arbitrary program runs. They differ from hardcoded-credential fixtures:
there is no MQTT credential. They differ from correctly protected MQTT topics:
the public ACL explicitly lets anonymous clients read the internal-data topics
without a maintenance access decision. None of the existing command-injection,
overflow, replay, sudo or other vulnerability packages is installed.

### Shared local build and testing

Run from the host repository root. Default machine is `qemuarm64`; use
`YOCTO_MACHINE` for the existing supported architecture selector.

~~~bash
# Parse the layer and resolve dependencies without compiling.
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe862-mqtt-internal-files'
# Build and boot a fixture.
FIRMWARE=router-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=router-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

From a second host terminal, fetch the exact internal-file content anonymously:

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
# Equivalent with locally installed Mosquitto clients; no username/password:
mosquitto_sub -h 127.0.0.1 -p 1883 -t device/config -C 1 -W 10
mosquitto_sub -h 127.0.0.1 -p 1883 -t maintenance/info -C 1 -W 10
# Protocol regression against the running fixture:
python3 scripts/test-mqtt-internal-files.py --device router
~~~

Expect the exact warning, fixture scope and exposure markers, with
`device_class=router` on `device/config`. The Python client uses MQTT 5 without
credentials. Regression verifies both exact payloads, wildcard access, public
write denial with MQTT 5 `Not authorized` PUBACK (`0x87`), denial even with
spoofed usernames, and no payloads for unknown/path-like topics. On the eight
MQTT-native profiles it also verifies normal peripheral telemetry.
`QEMU_MQTT_PORT` changes the loopback host TCP port; use the matching `--port`
in the test client. Existing HTTP and PLC Modbus forwards remain available.

Automatic disposable QEMU testing must run separately from manually booted QEMU:

~~~bash
python3 scripts/test-mqtt-internal-files.py --boot router
python3 scripts/test-mqtt-internal-files.py --all
# Example on Apple Silicon, with unused host ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-mqtt-internal-files.py --all
~~~

The automatic test uses the existing serial-console harness to change only the
synthetic internal config inside a throwaway guest snapshot. Its new probe
bytes must appear on `device/config`, proving real file origin. It then checks
missing/symlink/oversized/FIFO rejection and retained-data removal, restores the
original bytes, restarts the broker, and verifies topic recovery and a
loopback-bound publishing listener. None of these console probes is available
through MQTT. `validation-console.log` is stored beside each export.
The host client never scans or contacts non-loopback systems.

Offline inspection, with the builder's existing `debugfs` and `zstd` tools:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/router-cwe862-mqtt-internal-files/qemuarm64/iotbench-router-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

This verifies exact device/file contents and ownership, ELF topic mappings and
publish sink, installed analysis source/ground truth/warnings, locked service
account, enabled startup, broker configuration, ACLs and telemetry integration.
No host rootfs mount is needed. Build all eleven fixtures using:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe862-mqtt-internal-files.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

The existing `scripts/build-all.sh` discovers these images automatically.
Artifacts land in `deploy-images/<device>-cwe862-mqtt-internal-files/<machine>/`.

### Safe remediation

Remove the public `topic read device/config` and `topic read maintenance/info`
grants, or remove these private publications from the public broker. If
maintenance clients need them, authenticate those clients and authorize each
sensitive topic for a narrowly defined maintenance role. Encryption alone does
not enforce that topic-level decision. Preserve constant filenames, bounded
read-only behavior, unprivileged services and normal Unix file permissions.

A corrected variant must deny anonymous read access to both private topics,
continue denying public writes and unrelated reads, preserve public telemetry,
and allow only authorized maintenance subscribers. Rebuild the image after the
ACL/source change; disposable snapshots discard guest edits. The known-positive
anonymous exposure assertion must fail against the corrected image.

### Completed validation

On 2026-10-07, all eleven `qemuarm64` fixtures built and exported successfully
following BitBake layer parsing and a router dependency dry run. Offline
`debugfs` inspection of every compressed ext4 image verified exact synthetic
file contents/device identity, fixed topic/file mappings and publish sink in
the ELF, matching installed source/ground truth, locked UID/GID 991 account,
private `0640` files inside `0750`, enabled publisher/broker, active broker
configuration, ACLs, telemetry drop-in and required warning. Each manifest
contained exactly one vulnerability package, `cwe862-mqtt-internal-files`.
The publisher ELF was identical across all eleven images.

All eleven images passed in disposable QEMU snapshots with HVF/host CPU:
anonymous exact-file reads, wildcard disclosure, public write denial with
MQTT 5 `0x87` (also with spoofed usernames), no payloads from unknown/path-like
topics, actual file-origin probe, missing/symlink/oversized/FIFO rejection,
retained-content removal, original-byte restoration, broker restart and
private listener binding. All eight MQTT-native profiles also passed peripheral
telemetry checks. Tests used host-loopback MQTT 21883, HTTP 18080 and PLC
Modbus 11502; no external broker or infrastructure was contacted.

A separate disposable router control on host-loopback MQTT 22883 removed only
the two anonymous internal-topic read grants. Both disclosures stopped without
changing files or the publisher. Restoring those grants restored both exact
payloads, corroborating the topic authorization cause and remediation.

The [local validation report](../deploy-images/mqtt-internal-files-qemuarm64-validation.txt)
records results, rootfs/kernel/manifest checksums and source/ELF SHA-256 hashes.
Each export contains `rootfs.manifest`, `validation-console.log` and
`validation-protocol.log`. Build, offline, runtime and remediation logs are
under `deploy-images/mqtt-internal-files-*`. Other supported architectures were
not built or boot-tested. No external firmware-analysis engine was run; the
static finding remains expected ground truth supported by installed firmware
artifacts and real MQTT behavior.

### doorlock-cwe862-mqtt-internal-files

Simulated device: **access-control door lock**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/doorlock/`.
Firmware directory: `deploy-images/doorlock-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-doorlock-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/doorlock-cwe862-mqtt-internal-files/qemuarm64/iotbench-doorlock-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=doorlock`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=doorlock-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=doorlock-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device doorlock
~~~

Expected: exact internal bytes, `device_class=doorlock` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot doorlock` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/doorlock-cwe862-mqtt-internal-files/qemuarm64/iotbench-doorlock-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### envsensor-cwe862-mqtt-internal-files

Simulated device: **environmental sensor**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/envsensor/`.
Firmware directory: `deploy-images/envsensor-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-envsensor-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/envsensor-cwe862-mqtt-internal-files/qemuarm64/iotbench-envsensor-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=envsensor`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=envsensor-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=envsensor-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device envsensor
~~~

Expected: exact internal bytes, `device_class=envsensor` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot envsensor` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/envsensor-cwe862-mqtt-internal-files/qemuarm64/iotbench-envsensor-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### healthmonitor-cwe862-mqtt-internal-files

Simulated device: **health monitor**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/healthmonitor/`.
Firmware directory: `deploy-images/healthmonitor-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-healthmonitor-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/healthmonitor-cwe862-mqtt-internal-files/qemuarm64/iotbench-healthmonitor-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=healthmonitor`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device healthmonitor
~~~

Expected: exact internal bytes, `device_class=healthmonitor` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot healthmonitor` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/healthmonitor-cwe862-mqtt-internal-files/qemuarm64/iotbench-healthmonitor-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### ipcamera-cwe862-mqtt-internal-files

Simulated device: **surveillance IP camera**, retaining existing HTTP snapshot/MJPEG stream and web admin.
Device profile: `meta-iotbench/recipes-devices/ipcamera/`.
Firmware directory: `deploy-images/ipcamera-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-ipcamera-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/ipcamera-cwe862-mqtt-internal-files/qemuarm64/iotbench-ipcamera-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=ipcamera`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=ipcamera-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device ipcamera
~~~

Expected: exact internal bytes, `device_class=ipcamera` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot ipcamera` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/ipcamera-cwe862-mqtt-internal-files/qemuarm64/iotbench-ipcamera-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### plc-cwe862-mqtt-internal-files

Simulated device: **industrial PLC gateway**, retaining existing Modbus/TCP registers and web admin.
Device profile: `meta-iotbench/recipes-devices/plc/`.
Firmware directory: `deploy-images/plc-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-plc-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/plc-cwe862-mqtt-internal-files/qemuarm64/iotbench-plc-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=plc`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=plc-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=plc-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device plc
~~~

Expected: exact internal bytes, `device_class=plc` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot plc` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/plc-cwe862-mqtt-internal-files/qemuarm64/iotbench-plc-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### router-cwe862-mqtt-internal-files

Simulated device: **network router/gateway**, retaining existing HTTP web admin.
Device profile: `meta-iotbench/recipes-devices/router/`.
Firmware directory: `deploy-images/router-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-router-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/router-cwe862-mqtt-internal-files/qemuarm64/iotbench-router-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=router`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=router-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=router-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device router
~~~

Expected: exact internal bytes, `device_class=router` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot router` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/router-cwe862-mqtt-internal-files/qemuarm64/iotbench-router-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### smartbulb-cwe862-mqtt-internal-files

Simulated device: **lighting smart bulb**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/smartbulb/`.
Firmware directory: `deploy-images/smartbulb-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-smartbulb-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/smartbulb-cwe862-mqtt-internal-files/qemuarm64/iotbench-smartbulb-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=smartbulb`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=smartbulb-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device smartbulb
~~~

Expected: exact internal bytes, `device_class=smartbulb` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot smartbulb` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/smartbulb-cwe862-mqtt-internal-files/qemuarm64/iotbench-smartbulb-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### smarthub-cwe862-mqtt-internal-files

Simulated device: **controller/smart hub**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/smarthub/`.
Firmware directory: `deploy-images/smarthub-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-smarthub-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/smarthub-cwe862-mqtt-internal-files/qemuarm64/iotbench-smarthub-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=smarthub`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=smarthub-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=smarthub-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device smarthub
~~~

Expected: exact internal bytes, `device_class=smarthub` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot smarthub` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/smarthub-cwe862-mqtt-internal-files/qemuarm64/iotbench-smarthub-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### smartplug-cwe862-mqtt-internal-files

Simulated device: **energy-management smart plug**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/smartplug/`.
Firmware directory: `deploy-images/smartplug-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-smartplug-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/smartplug-cwe862-mqtt-internal-files/qemuarm64/iotbench-smartplug-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=smartplug`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=smartplug-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=smartplug-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device smartplug
~~~

Expected: exact internal bytes, `device_class=smartplug` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot smartplug` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/smartplug-cwe862-mqtt-internal-files/qemuarm64/iotbench-smartplug-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### smartspeaker-cwe862-mqtt-internal-files

Simulated device: **audio smart speaker**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/smartspeaker/`.
Firmware directory: `deploy-images/smartspeaker-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-smartspeaker-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/smartspeaker-cwe862-mqtt-internal-files/qemuarm64/iotbench-smartspeaker-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=smartspeaker`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device smartspeaker
~~~

Expected: exact internal bytes, `device_class=smartspeaker` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot smartspeaker` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/smartspeaker-cwe862-mqtt-internal-files/qemuarm64/iotbench-smartspeaker-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### thermostat-cwe862-mqtt-internal-files

Simulated device: **climate-control thermostat**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/thermostat/`.
Firmware directory: `deploy-images/thermostat-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-thermostat-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/thermostat-cwe862-mqtt-internal-files/qemuarm64/iotbench-thermostat-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=thermostat`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=thermostat-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=thermostat-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device thermostat
~~~

Expected: exact internal bytes, `device_class=thermostat` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot thermostat` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/thermostat-cwe862-mqtt-internal-files/qemuarm64/iotbench-thermostat-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

## Vulnerable Bash Files — Path Traversal (CWE-22)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario and expected ground truth

The eleven `<device>-cwe022-bash-path-traversal` firmware images reuse the common image,
existing device profiles, native services, peripheral simulator, pinned Yocto
layers and build/export scripts. Each installs exactly one vulnerability
package, `cwe022-bash-path-traversal`, with a local Bash helper and synthetic data.

The exact expected ground-truth label is **Vulnerable Bash files — Path
Traversal**; the weakness is **CWE-22 — Path Traversal**. The vulnerability is
specifically **Path Traversal in a Bash firmware helper caused by concatenating
user-controlled path input with an intended base directory without sufficient
canonicalization or boundary validation**. The local caller controls the
helper's first argument. No network input or additional service is needed.

`/usr/bin/iotbench-bash-read` has an actual `#!/bin/bash` interpreter and an
explicit `bash` runtime dependency. Its vulnerable flow is:

~~~bash
BASE_DIR='/usr/share/iotbench/bash-path-traversal/data/'
INPUT="$1"
TARGET="${BASE_DIR}${INPUT}"
# No canonicalization, normalization or data/ boundary validation.
while IFS= read -r line || [[ -n "$line" ]]; do
    printf '%s\n' "$line"
done < "$TARGET"
~~~

A representative positive is:

~~~text
input "../internal/private-fixture.txt"
→ /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ synthetic internal file read
→ SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

The kernel resolves `data/..` to the parent directory, so `internal/` is a
sibling of `data/`, outside the intended directory. Bash does not require the
resolved target to stay under `BASE_DIR`. The `[[ -f "$TARGET" ]]` check only
requires a regular file; it is not traversal validation and accepts the
internal file. Input and redirection are quoted. Shell metacharacters in `$1`
remain literal filename bytes, with no `eval`, command substitution on input,
`sh -c`, arbitrary command execution or command injection. Reading and printing
use Bash builtins, without a subprocess, writes, networking or package manager.

Detection requires the complete relationship **Bash input + filesystem path
construction + intended base directory + missing traversal validation +
filesystem access outside that intended directory**. Merely accepting an
argument or reading a file is insufficient. An analyzer should trace `$1` to
`INPUT`, then `TARGET`, and to the quoted redirection / `read` sink, identify the
absent `data/` boundary check, and correlate the sibling synthetic file.
`ground-truth.json` records the expected finding; it is not a substitute for
analyzing the actual installed Bash script.

These fixtures differ from generic vulnerable Java/JAR applications and
generic vulnerable C binaries because the actual vulnerable input-to-read flow
is in a Bash helper installed in every device firmware. They differ from
ordinary Bash scripts without attacker-controlled paths and generic fixed-name
file readers because the first argument selects the constructed target. They
differ from command injection and arbitrary command-execution examples because
input is used only as a quoted filesystem path. They differ from unsafe sudo
helper examples because no sudo rule, privileged read grant or SUID is added.
They differ from Path Traversal in unrelated applications because the firmware
Bash helper is the measured source and sink.

### Filesystem layout and independent lab containment

The repository convention is `/usr/bin` for local helpers and
`/usr/share/iotbench/<scenario>` for local fixture assets. Sources are under
`meta-iotbench/recipes-vulns/cwe022-bash-path-traversal/`; all local `file://` inputs
are deterministic. No new firmware architecture or device profile is created.

| Artifact | Firmware path / role |
| --- | --- |
| Vulnerable Bash helper | `/usr/bin/iotbench-bash-read`, root:root `0755` |
| Intended base directory, as seen by the confined helper | `/usr/share/iotbench/bash-path-traversal/data/` |
| Intended file, as seen by the confined helper | `/usr/share/iotbench/bash-path-traversal/data/public.txt`; `SYNTHETIC_PUBLIC_FIXTURE_DATA` |
| Internal file, as seen by the confined helper | `/usr/share/iotbench/bash-path-traversal/internal/private-fixture.txt`; `SYNTHETIC_INTERNAL_FIXTURE_DATA` |
| Fixed outer process root | `/usr/share/iotbench/bash-path-traversal/rootfs/` |
| Public file in the extracted firmware | `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/data/public.txt`, root:root `0644` |
| Internal file in the extracted firmware | `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/internal/private-fixture.txt`, root:root `0644` |
| Safe loadable Bash builtin | `/usr/lib/iotbench/bash-path-traversal/fixture-confine.so`, root:root `0755` |
| Analysis metadata / notice / guest regression | `ground-truth.json`, `NOTICE`, `test-guest.sh` under `/usr/share/iotbench/bash-path-traversal/` |
| Containment source for inspection | `/usr/share/iotbench/bash-path-traversal/fixture-confine.c` |

The helper first loads `fixture_confine` into the already initialized Bash
process and invokes it with **no arguments**. The builtin enters only the
fixed outer `rootfs/`, sets its working directory to `/`, removes supplementary
groups, permanently drops to UID/GID `990:990` and forbids new privileges.
No account, password, privileged login or permission grant is created. A
non-root caller cannot perform confinement and is rejected; run tests from the
existing guest root serial console. Partial confinement failure terminates
the process before any user-controlled file read.

This small C module has no `main()`, never reads files, never receives the
supplied path and never constructs or validates `TARGET`. It is solely a safe
Bash loadable confinement builtin, compiled against the pinned Bash headers
using Yocto's normal cross compiler. It does not launch Bash or another shell;
it executes inside the existing interpreter. Its source is installed for
analysis. The package's MIT/GPL-compatible licensing is recorded in the recipe.

The jail contains **only the two synthetic regular files and root-owned `0755`
directories**. It has no executables, libraries, symlinks, device nodes,
`/proc`, host mounts or system files. Bash and the builtin are loaded before
the root change; all later operations are interpreter builtins. Even many
`../` segments cannot leave that process root. Both synthetic files remain
readable after dropping privileges. The word "private" describes the intended
application directory boundary, not a root-only permissions scenario.

This is containment of the entire lab, **not** enforcement of the intended
`data/` boundary. It leaves `../internal/private-fixture.txt` vulnerable and
adds none of the prohibited vulnerable-path mitigations: no `realpath`,
`readlink -f`, canonical path comparison, rejection of `..`, filename allowlist
or basename-only enforcement. The image postprocess asserts the two-file jail
layout and ordinary permissions, and appends the exact NOTICE to `/etc/motd`.
The helper prints the warning on each invocation. No host paths, real secrets,
credentials, persistence or system security setting changes are part of it.

### Shared local build and testing

Run host commands from the repository root. Default machine: `qemuarm64`.
Use `YOCTO_MACHINE` consistently for the existing other supported architectures.
Parse and resolve dependencies with the existing builder:

~~~bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe022-bash-path-traversal'
~~~

Build all eleven fixtures:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe022-bash-path-traversal.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

Exports use `deploy-images/<device>-cwe022-bash-path-traversal/<machine>/` and the
existing `scripts/build-all.sh` automatically includes all new image recipes.
For manual testing, boot the selected firmware with `scripts/run-qemu.sh` and
log into its serial console with the common lab `root` / `routeradmin` login.
Run only **inside the guest**:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh router
~~~

Expected: exact warning followed by public marker; then warning followed by
internal marker; then five `PASS` lines and status zero. Missing or non-regular
files return 1, and incorrect argument count or failed confinement returns 2.
The guest regression verifies normal reads, two traversal spellings, argument
counts, missing/directory paths, literal shell-shaped filenames, deep traversal
containment and ordinary helper permissions. Its outside-jail probes reference
only this fixture's synthetic NOTICE and data, never real system secrets.
It checks that the jail has exactly two files and no symlinks or special files.
The helper and regression do not mutate files.

`scripts/test-bash-path-traversal.py --image <ext4-or-ext4.zst>` uses `debugfs`
without mounting or executing the firmware. It verifies the exact installed
Bash/source/test/metadata, actual Bash interpreter, fixed confinement ELF,
recursive jail contents and ownership, file bytes, ancestors and warning.
Expected: two `PASS` lines. Use the builder's installed tools as in the
per-device commands below.

For automatic disposable guest boots, separately from manually running QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device router
python3 scripts/test-bash-path-traversal.py --all
# Optional Apple Silicon acceleration and unused existing device-service ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-bash-path-traversal.py --all
~~~

The runner needs host QEMU and `zstd`, boots one snapshot at a time, invokes
the regression over the serial console and closes QEMU. Logs are saved beside
each export as `validation-console.log`. The path-traversal helper uses no
networking; port settings support only the unchanged device profiles.

### Safe remediation

In a separate corrected variant, resolve the supplied path relative to a trusted
`data/` directory and enforce that the resolved file remains inside it. Reject
absolute paths and escaping traversal; account for symlinks and filesystem
races, preferably using directory-relative opens with resolution constraints.
A lexical prefix comparison alone is insufficient. Keep quoted input and
read-only behavior, ordinary file permissions and the outer synthetic jail.
Rebuild for a lasting variant; do not add the fix to these known-positive
vulnerable fixtures. A corrected variant must still read `public.txt` but reject
`../internal/private-fixture.txt` without printing the internal marker. The
vulnerable fixture's positive traversal assertion must fail against that fix.

### Completed validation

On 2026-10-07, all eleven `qemuarm64` firmware fixtures built and exported
successfully after BitBake layer parsing and a router dependency dry run.
Every image manifest contains exactly one vulnerability package,
`cwe022-bash-path-traversal`, plus the actual Bash runtime and its existing
device profile. No other vulnerability package was added.

Offline `debugfs` inspection of all eleven compressed ext4 exports verified
exact installed Bash, confinement source, guest regression and ground truth;
the fixed confinement ELF; the actual Bash interpreter; device identity;
ordinary root:root `0755` helper/builtin permissions; root:root `0644` synthetic
files; safe ancestor directories; recursive two-file jail contents with no
symlinks or special files; and the required NOTICE/login warning. Installed
Bash helper and confinement builtin bytes are identical across all images.

All eleven images booted in disposable QEMU snapshots with HVF/host CPU and
passed all five guest regression groups: intended public-file read, two `../`
traversal spellings reading the synthetic internal marker, invalid arguments
and literal shell-shaped filenames, deep traversal remaining inside the
synthetic-only jail, and ordinary permissions without SUID or sudo grants.
Tests used the local serial console and existing host-loopback device-service
ports HTTP `18080`, MQTT `21883` and PLC Modbus `11502`. The Bash helper itself
uses no networking and neither it nor the guest regression modifies files.

The [local validation report](../deploy-images/bash-path-traversal-qemuarm64-validation.txt)
records all 55 guest checks and compressed-rootfs/kernel/manifest/console/source
SHA-256 checksums. Each export includes `rootfs.manifest` and
`validation-console.log`; aggregate logs are saved under
`deploy-images/bash-path-traversal-qemuarm64-*`. Other supported architectures
were not built or boot-tested. No external firmware-analysis engine was run;
the static finding is expected ground truth supported by the installed Bash
flow and observed local traversal behavior.

### doorlock-cwe022-bash-path-traversal

Simulated device: **access-control door lock**, using the existing
`meta-iotbench/recipes-devices/doorlock/` profile. Firmware directory:
`deploy-images/doorlock-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-doorlock-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/doorlock-cwe022-bash-path-traversal/qemuarm64/iotbench-doorlock-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=doorlock-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=doorlock-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh doorlock
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/doorlock-cwe022-bash-path-traversal/qemuarm64/iotbench-doorlock-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device doorlock
~~~

### envsensor-cwe022-bash-path-traversal

Simulated device: **environmental sensor**, using the existing
`meta-iotbench/recipes-devices/envsensor/` profile. Firmware directory:
`deploy-images/envsensor-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-envsensor-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/envsensor-cwe022-bash-path-traversal/qemuarm64/iotbench-envsensor-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=envsensor-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=envsensor-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh envsensor
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/envsensor-cwe022-bash-path-traversal/qemuarm64/iotbench-envsensor-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device envsensor
~~~

### healthmonitor-cwe022-bash-path-traversal

Simulated device: **health monitor**, using the existing
`meta-iotbench/recipes-devices/healthmonitor/` profile. Firmware directory:
`deploy-images/healthmonitor-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/healthmonitor-cwe022-bash-path-traversal/qemuarm64/iotbench-healthmonitor-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh healthmonitor
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/healthmonitor-cwe022-bash-path-traversal/qemuarm64/iotbench-healthmonitor-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device healthmonitor
~~~

### ipcamera-cwe022-bash-path-traversal

Simulated device: **surveillance IP camera**, using the existing
`meta-iotbench/recipes-devices/ipcamera/` profile. Firmware directory:
`deploy-images/ipcamera-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/ipcamera-cwe022-bash-path-traversal/qemuarm64/iotbench-ipcamera-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=ipcamera-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh ipcamera
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/ipcamera-cwe022-bash-path-traversal/qemuarm64/iotbench-ipcamera-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device ipcamera
~~~

### plc-cwe022-bash-path-traversal

Simulated device: **industrial PLC gateway (OT)**, using the existing
`meta-iotbench/recipes-devices/plc/` profile. Firmware directory:
`deploy-images/plc-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-plc-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/plc-cwe022-bash-path-traversal/qemuarm64/iotbench-plc-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=plc-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=plc-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh plc
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/plc-cwe022-bash-path-traversal/qemuarm64/iotbench-plc-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device plc
~~~

### router-cwe022-bash-path-traversal

Simulated device: **network gateway router**, using the existing
`meta-iotbench/recipes-devices/router/` profile. Firmware directory:
`deploy-images/router-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-router-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/router-cwe022-bash-path-traversal/qemuarm64/iotbench-router-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=router-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=router-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh router
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/router-cwe022-bash-path-traversal/qemuarm64/iotbench-router-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device router
~~~

### smartbulb-cwe022-bash-path-traversal

Simulated device: **lighting controller / smart bulb**, using the existing
`meta-iotbench/recipes-devices/smartbulb/` profile. Firmware directory:
`deploy-images/smartbulb-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/smartbulb-cwe022-bash-path-traversal/qemuarm64/iotbench-smartbulb-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=smartbulb-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh smartbulb
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/smartbulb-cwe022-bash-path-traversal/qemuarm64/iotbench-smartbulb-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device smartbulb
~~~

### smarthub-cwe022-bash-path-traversal

Simulated device: **smart-home controller / hub**, using the existing
`meta-iotbench/recipes-devices/smarthub/` profile. Firmware directory:
`deploy-images/smarthub-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smarthub-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/smarthub-cwe022-bash-path-traversal/qemuarm64/iotbench-smarthub-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smarthub-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=smarthub-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh smarthub
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/smarthub-cwe022-bash-path-traversal/qemuarm64/iotbench-smarthub-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device smarthub
~~~

### smartplug-cwe022-bash-path-traversal

Simulated device: **energy-management smart plug**, using the existing
`meta-iotbench/recipes-devices/smartplug/` profile. Firmware directory:
`deploy-images/smartplug-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartplug-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/smartplug-cwe022-bash-path-traversal/qemuarm64/iotbench-smartplug-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartplug-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=smartplug-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh smartplug
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/smartplug-cwe022-bash-path-traversal/qemuarm64/iotbench-smartplug-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device smartplug
~~~

### smartspeaker-cwe022-bash-path-traversal

Simulated device: **audio / voice-assistant speaker**, using the existing
`meta-iotbench/recipes-devices/smartspeaker/` profile. Firmware directory:
`deploy-images/smartspeaker-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/smartspeaker-cwe022-bash-path-traversal/qemuarm64/iotbench-smartspeaker-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh smartspeaker
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/smartspeaker-cwe022-bash-path-traversal/qemuarm64/iotbench-smartspeaker-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device smartspeaker
~~~

### thermostat-cwe022-bash-path-traversal

Simulated device: **climate-control thermostat**, using the existing
`meta-iotbench/recipes-devices/thermostat/` profile. Firmware directory:
`deploy-images/thermostat-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-thermostat-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/thermostat-cwe022-bash-path-traversal/qemuarm64/iotbench-thermostat-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=thermostat-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=thermostat-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh thermostat
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/thermostat-cwe022-bash-path-traversal/qemuarm64/iotbench-thermostat-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device thermostat
~~~

## Vulnerable C Binaries — SQL injection (CWE-89)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario, source and sink

Each of the eleven existing profiles has one new `<device>-cwe089-c-sql-injection`
firmware with the sole vulnerability package `cwe089-c-sql-injection`. They reuse
the common image, native services, simulated peripherals, pinned layers,
architecture selector, cross compiler and export/QEMU mechanisms. The canonical
input is a local command-line argument, so no web module or remote input is needed.

Expected exact ground-truth label: **Vulnerable C Binaries — SQL injection**.
Expected finding: **CWE-89**, externally controlled SQL syntax in a native C
firmware executable exposing an additional synthetic record through SELECT.
The full required relationship is **C binary input + SQL query construction +
user-controlled value inserted into SQL syntax + missing secure parameter
binding + SQLite query execution + modified query semantics**.

The corresponding source is
[`fixture-db-query.c`](../meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c).
Exact locations (also installed as the same source in the firmware):

| Stage | Source location | Meaning |
| --- | --- | --- |
| Source | `main()`, lines 50–54 | Length-check `argv[1]` and assign `input` |
| Transformation / missing protection | `main()`, lines 57–59 | `snprintf()` directly embeds `input` in `WHERE record_name = '%s'`; no binding or SQL escaping |
| Database open | `main()`, line 65 | Fixed path, `sqlite3_open_v2(..., SQLITE_OPEN_READONLY, NULL)` |
| Preparation sink | `main()`, line 77 | `sqlite3_prepare_v2(db, query, -1, &stmt, &tail)` consumes the constructed SQL |
| Execution sink | `main()`, line 81 | `sqlite3_step(stmt)` executes the SELECT and retrieves rows |
| Consequence | `main()`, lines 84–86 | `sqlite3_column_text()` and fixed-format `printf()` return synthetic values |

Representative vulnerable flow and expected static-analysis data flow:

~~~text
argv[1] = "public' OR '1'='1" → input
→ snprintf() constructs SQL query
→ SELECT record_name, record_value FROM fixture_records
  WHERE record_name = 'public' OR '1'='1' ORDER BY id;
→ sqlite3_prepare_v2() → sqlite3_step() → sqlite3_column_text()
→ synthetic internal database record returned: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

The quote closes the intended SQL value; `OR '1'='1'` becomes an always-true
SQL predicate, so both rows match. Normal `public` produces only
`WHERE record_name = 'public' ORDER BY id;`, selecting row 1. The program intends
a single named lookup. It instead treats externally controlled text as SQL
syntax rather than a bound SQL value. `sqlite3_prepare_v2()` alone is not safe
parameterization: the vulnerability is already present in the SQL it receives.
There is no `sqlite3_bind_text()`, integer binding, placeholder, `%q` escaping,
quote/operator filtering, value allowlist or query rewriting in this code path.

These are not generic vulnerable Java/JAR applications, SQL injection in Java,
PHP or Python, or Bash-based vulnerabilities. Only the native C executable
constructs and executes the vulnerable query; shell/Python code is test harness
code. This differs from generic C argument consumers, C database openers, fixed
SQLite query programs and correctly parameterized applications: accepting an
argument, opening a database or executing a fixed query alone is insufficient.
The complete source-to-SQL-to-execution relationship is required. These are not
buffer overflow, memory corruption, command injection, arbitrary command
execution or unsafe sudo helper examples. The C program never invokes a shell,
process, package manager or network API and adds no SUID, sudo rule, login,
privilege grant or unrelated application outside the firmware.

### Database, packaging and runtime scope

| Artifact | Firmware path / role |
| --- | --- |
| Vulnerable native ELF executable | `/usr/bin/fixture-db-query`, root:root `0755` |
| Synthetic SQLite database | `/usr/share/iotbench/c-sql-injection/fixture.db`, root:root `0444` |
| Matching C source | `/usr/share/iotbench/c-sql-injection/fixture-db-query.c` |
| Supporting firmware assets | `schema.sql`, `NOTICE`, `LICENSE`, `ground-truth.json`, `test-guest.sh` in the same data directory, root:root `0644` |
| Repository package / source directory | `meta-iotbench/recipes-vulns/cwe089-c-sql-injection/` / `files/` |

The schema is `fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL
UNIQUE, record_value TEXT NOT NULL, visibility TEXT NOT NULL)`, with a CHECK
restricting `visibility` to `public` or `internal`. Its exact two rows are:

| id | record_name | record_value | visibility |
| --- | --- | --- | --- |
| 1 | public | SYNTHETIC_PUBLIC_FIXTURE_DATA | public |
| 2 | internal | SYNTHETIC_INTERNAL_FIXTURE_DATA | internal |

All values are synthetic, contain no credentials or real data, and are identical
across profiles. "Internal" denotes the extra record outside the normal public
lookup result, not an OS permission boundary or a separate authentication bug.
`schema.sql` creates records only during the build using `sqlite3-native`;
there is no runtime creation, modification, deletion or schema change. The
recipe recreates the database from scratch with fixed page size and ordered
rows. The database format is portable across the existing target architectures.

The package uses `${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS}`, links `-lsqlite3`,
and depends on `sqlite3 sqlite3-native` from the already pinned core layer.
Yocto supplies the cross compiler, target headers/library, shared-library
runtime dependency and native database generator. The target SQLite CLI and
Python are unnecessary. `util-linux-setpriv` is used only by the guest test to
prove unprivileged execution. File layout and permissions follow the existing
local-helper convention; there is no new firmware architecture or service.

The executable opens only its compiled fixed database path (no filename/env
argument, URI flag or host database). It enforces a read-only connection and a
single read-only two-column statement, finalizes it and closes the connection.
An independent SQLite authorizer permits only SELECT and reads from
`main.fixture_records`; it denies other tables, ATTACH, SQL functions and all
write operations. Extension loading is explicitly disabled. These restrictions
contain the lab to synthetic data; they do not inspect or constrain WHERE
predicates, and the required OR injection remains effective. Input is capped
at 240 bytes solely for bounded storage, `snprintf()` is checked, and SQLite
errors and null column pointers are handled. A progress budget, expression and
value limits and a 16-row output cap bound work. Output uses a constant format.
No external database, credentials, sockets, host filesystem writes, persistence
or system security changes are involved. The helper needs no root privileges.
The exact warning appears in package NOTICE, `/etc/motd` and helper stderr.

### Shared build and local verification

From the host repository root, parse and resolve dependencies:

~~~bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe089-c-sql-injection'
~~~

Build all eleven with the existing process:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe089-c-sql-injection.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

Default machine is `qemuarm64`. Set the same `YOCTO_MACHINE` for build and boot
for `qemuarm`, `qemux86-64`, `qemux86` or `qemumips`. The recipes contain no fixed
CPU or toolchain; architecture builds use the established Yocto conventions.
`scripts/build-all.sh` automatically discovers the new recipes.

The guest test has six assertion groups: native ELF/database installation and
ordinary permissions; deterministic public-only lookup and absent-name behavior;
the exact injection returning both records; argument counts, length boundaries,
malformed SQL and literal shell-shaped values; extra-statement/schema/function
rejection; and non-root execution with unchanged database checksum and no journal
sidecars. All lookup invocations use UID/GID 65534 with cleared supplementary
groups. It uses only benign SELECT payloads and never modifies the database.
A hardened parameterized replacement would fail the intended positive injection
assertion. Exit codes are 0 for successful queries (including zero matches),
1 for SQLite/scope failures, and 2 for argument/length errors.

`scripts/test-c-sql-injection.py --image <ext4-or-ext4.zst>` reads firmware with
`debugfs` without mounting or executing it, verifies ELF SQLite API references
and fixed path, exact source/assets, normal ownership/modes and safe ancestors,
warning, schema and both synthetic rows. It opens only a temporary copy of the
extracted synthetic database with Python SQLite `mode=ro&immutable=1`; Python
is test infrastructure, not the vulnerability implementation. Expected output:
two `PASS` lines. The builder's cached `e2fsprogs-native` provides `debugfs`;
use `--debugfs` if it is not on PATH (see the per-device examples).

Automatic runtime tests use the existing serial console in disposable QEMU
snapshots, close QEMU on completion and save `validation-console.log` beside
each export. Run separately from manual QEMU:

~~~bash
python3 scripts/test-c-sql-injection.py --device router
python3 scripts/test-c-sql-injection.py --all
# Apple Silicon acceleration and unused existing device-service ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-c-sql-injection.py --all
~~~

The runner requires host QEMU and `zstd`. Tests need no internet or external
service. Host-loopback forwards support only the unchanged device services;
the SQL helper itself has no network surface.

### Safe remediation

In a separate corrected variant, prepare this constant SQL:

~~~sql
SELECT record_name, record_value FROM fixture_records
WHERE record_name = ? ORDER BY id;
~~~

Call `sqlite3_prepare_v2()` on that fixed query, then
`sqlite3_bind_text(stmt, 1, input, -1, SQLITE_TRANSIENT)`, check return codes,
and use `sqlite3_step()` before finalizing and closing. The input then remains
a value even when it contains quotes or SQL operators. Keep the read-only
connection, bounded input and ordinary permissions. Normal `public` must still
return its marker; the crafted string must return no row and no internal
marker. The intentionally vulnerable fixtures do not implement this fix.

### Completed validation

On 2026-10-16, all eleven `qemuarm64` fixtures built and exported successfully
using the pinned builder after clean layer parsing and a router dependency dry
run. Each exported manifest contains exactly one vulnerability package,
`cwe089-c-sql-injection`, and the target `libsqlite3-0` shared library. The native
C helper compiled with `-Wall -Wextra -Werror` and the normal Yocto flags.

Offline `debugfs` verification passed for every compressed ext4 image: actual
native ELF and SQLite API references, compiled fixed database path, exact
installed source/schema/test/metadata, two synthetic records and database
integrity, ordinary root-owned permissions and safe ancestors, device identity
and required NOTICE/login warning. Helper and database bytes are identical
across all eleven images. Two fresh database generations using the pinned
`sqlite3-native` matched each other and the installed database byte for byte.

All eleven images then booted as disposable QEMU snapshots with HVF/host CPU
and passed all six guest assertion groups, **66 checks total**. The exact
normal lookup returned only the public marker; the exact injection returned
both public and internal markers. Every lookup ran as UID/GID 65534 with cleared
groups. Argument and length boundaries, malformed SQL, literal shell-shaped
input, extra statements, non-fixture tables and SQL functions behaved as
specified; the database checksum stayed unchanged and no journal sidecar
appeared. Tests used only the local serial console and existing device-service
host-loopback ports HTTP `18080`, MQTT `21883` and Modbus `11502`. The SQL helper
uses no network. The guest checks use commands supported by the pinned BusyBox
configuration and do not modify the database.

The [local validation report](../deploy-images/c-sql-injection-qemuarm64-validation.txt)
records all 66 assertions and SHA-256 checksums for compressed rootfs, kernel,
manifest, console logs and implementation sources. Each device export contains
`rootfs.manifest` and `validation-console.log`; aggregate build, parse, offline,
runtime and database-determinism logs are under
`deploy-images/c-sql-injection-qemuarm64-*`. Other supported architectures were
not built or boot-tested. No external static-analysis engine was run; CWE-89
is the expected ground truth supported by the installed C flow and reproduced
SQL behavior.

### doorlock-cwe089-c-sql-injection

Simulated device: **access-control door lock**, reusing
`meta-iotbench/recipes-devices/doorlock/`. Firmware directory:
`deploy-images/doorlock-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-doorlock-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=doorlock-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=doorlock-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh doorlock
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/doorlock-cwe089-c-sql-injection/qemuarm64/iotbench-doorlock-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device doorlock
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/doorlock-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/doorlock-cwe089-c-sql-injection/qemuarm64/iotbench-doorlock-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### envsensor-cwe089-c-sql-injection

Simulated device: **environmental sensor**, reusing
`meta-iotbench/recipes-devices/envsensor/`. Firmware directory:
`deploy-images/envsensor-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-envsensor-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=envsensor-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=envsensor-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh envsensor
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/envsensor-cwe089-c-sql-injection/qemuarm64/iotbench-envsensor-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device envsensor
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/envsensor-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/envsensor-cwe089-c-sql-injection/qemuarm64/iotbench-envsensor-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### healthmonitor-cwe089-c-sql-injection

Simulated device: **health monitor**, reusing
`meta-iotbench/recipes-devices/healthmonitor/`. Firmware directory:
`deploy-images/healthmonitor-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh healthmonitor
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/healthmonitor-cwe089-c-sql-injection/qemuarm64/iotbench-healthmonitor-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device healthmonitor
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/healthmonitor-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/healthmonitor-cwe089-c-sql-injection/qemuarm64/iotbench-healthmonitor-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### ipcamera-cwe089-c-sql-injection

Simulated device: **surveillance IP camera**, reusing
`meta-iotbench/recipes-devices/ipcamera/`. Firmware directory:
`deploy-images/ipcamera-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=ipcamera-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh ipcamera
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/ipcamera-cwe089-c-sql-injection/qemuarm64/iotbench-ipcamera-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device ipcamera
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/ipcamera-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/ipcamera-cwe089-c-sql-injection/qemuarm64/iotbench-ipcamera-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### plc-cwe089-c-sql-injection

Simulated device: **industrial PLC gateway (OT)**, reusing
`meta-iotbench/recipes-devices/plc/`. Firmware directory:
`deploy-images/plc-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-plc-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=plc-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=plc-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh plc
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/plc-cwe089-c-sql-injection/qemuarm64/iotbench-plc-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device plc
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/plc-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/plc-cwe089-c-sql-injection/qemuarm64/iotbench-plc-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### router-cwe089-c-sql-injection

Simulated device: **network router / gateway**, reusing
`meta-iotbench/recipes-devices/router/`. Firmware directory:
`deploy-images/router-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-router-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=router-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=router-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh router
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/router-cwe089-c-sql-injection/qemuarm64/iotbench-router-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device router
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/router-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/router-cwe089-c-sql-injection/qemuarm64/iotbench-router-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### smartbulb-cwe089-c-sql-injection

Simulated device: **lighting / smart bulb**, reusing
`meta-iotbench/recipes-devices/smartbulb/`. Firmware directory:
`deploy-images/smartbulb-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=smartbulb-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh smartbulb
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartbulb-cwe089-c-sql-injection/qemuarm64/iotbench-smartbulb-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device smartbulb
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/smartbulb-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/smartbulb-cwe089-c-sql-injection/qemuarm64/iotbench-smartbulb-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### smarthub-cwe089-c-sql-injection

Simulated device: **controller / smart hub**, reusing
`meta-iotbench/recipes-devices/smarthub/`. Firmware directory:
`deploy-images/smarthub-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smarthub-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smarthub-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=smarthub-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh smarthub
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smarthub-cwe089-c-sql-injection/qemuarm64/iotbench-smarthub-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device smarthub
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/smarthub-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/smarthub-cwe089-c-sql-injection/qemuarm64/iotbench-smarthub-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### smartplug-cwe089-c-sql-injection

Simulated device: **energy-management smart plug**, reusing
`meta-iotbench/recipes-devices/smartplug/`. Firmware directory:
`deploy-images/smartplug-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartplug-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartplug-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=smartplug-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh smartplug
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartplug-cwe089-c-sql-injection/qemuarm64/iotbench-smartplug-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device smartplug
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/smartplug-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/smartplug-cwe089-c-sql-injection/qemuarm64/iotbench-smartplug-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### smartspeaker-cwe089-c-sql-injection

Simulated device: **audio / voice-assistant speaker**, reusing
`meta-iotbench/recipes-devices/smartspeaker/`. Firmware directory:
`deploy-images/smartspeaker-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh smartspeaker
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartspeaker-cwe089-c-sql-injection/qemuarm64/iotbench-smartspeaker-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device smartspeaker
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/smartspeaker-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/smartspeaker-cwe089-c-sql-injection/qemuarm64/iotbench-smartspeaker-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### thermostat-cwe089-c-sql-injection

Simulated device: **climate-control thermostat**, reusing
`meta-iotbench/recipes-devices/thermostat/`. Firmware directory:
`deploy-images/thermostat-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-thermostat-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=thermostat-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=thermostat-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh thermostat
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/thermostat-cwe089-c-sql-injection/qemuarm64/iotbench-thermostat-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device thermostat
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/thermostat-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/thermostat-cwe089-c-sql-injection/qemuarm64/iotbench-thermostat-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

## Vulnerable C Binaries — Null Pointer Dereference (CWE-476)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario and source-to-sink ground truth

Exact ground-truth label: **Vulnerable C Binaries — Null Pointer Dereference**.
Classification: **CWE-476: NULL Pointer Dereference**. Eleven independent image
recipes combine each existing device profile with the single vulnerability
package `cwe476-null-pointer-dereference`. Their purpose is offline, authorized
static-analysis research using synthetic firmware. Runtime validation is optional
and confined to disposable local environments.

The harmless operation is a named lookup of synthetic device information.
`fixture-device-info.c` contains the entire vulnerable flow; it is stored in
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/` and installed
with its matching native ELF executable. No runtime switch selects other flaws.

| Ground-truth element | Exact location in `fixture-device-info.c` |
| --- | --- |
| Synthetic records | Lines 12–15: ID 1, `public`, `SYNTHETIC_PUBLIC_FIXTURE_DATA`; ID 2, `status`, `SYNTHETIC_STATUS_FIXTURE_DATA` |
| Argument validation | Lines 33–36: require exactly one record-name argument before reading `argv[1]` |
| External input | Line 38: `const char *input = argv[1];` |
| Pointer-returning lookup | Lines 17–27: `lookup_record(const char *name)` loops over both records and uses `strcmp()` |
| Found-record pointer | Line 23: `return &records[i];` |
| Reachable NULL return | Line 26: `return NULL;` after every comparison fails |
| Nullable result variable | Line 39: `const fixture_record_t *record = lookup_record(input);` |
| Intentionally missing validation | Between assignment at line 39 and first member access at line 43; explicit comment at lines 41–42 |
| First unsafe sink | Line 43: `printf("Record ID: %d\n", record->id);` |
| Subsequent member access | Line 44: `record->value` (the first access already faults for NULL on the tested target) |

Representative vulnerable flow, identical in every device:

`input "missing-record"` → `lookup_record(input)` → `return NULL` →
`record = NULL` → `no NULL check` → `record->id` → `Null Pointer Dereference`.

`missing-record` is absent from the compiled table, so ordinary lookup logic
selects the NULL path. There is no hardcoded unconditional NULL assignment,
manual fault signal, `abort()`, fallback record, default pointer, input allowlist,
defensive replacement or early return protecting this path. Unknown names,
including the empty string, also reach the same intended defect. There is no
input copy, input-sized allocation or writable input buffer. Loops are bounded
by the initialized table; output format strings are constant.

Expected static finding: a user-controlled argument reaches a pointer-returning
lookup, whose unsuccessful-search path returns NULL to local variable `record`;
the caller reaches its structure-member load without a NULL check. Merely
accepting input, using pointers, returning NULL or crashing does not establish
this relationship. The complete input-dependent flow is required.

This is native C, with neither Java/JAR applications nor Java Null Pointer
Exceptions. Bash and Python files are test harnesses only. It differs from
unspecified generic vulnerable C binaries and generic application crashes because
the precise nullable return and unchecked structure-member access are identified.
It is not a buffer overflow, use-after-free, double-free, uninitialized pointer,
out-of-bounds access or arbitrary pointer dereference: the only possible result
is a pointer to one of two initialized static records or NULL. There are no
user-selected addresses, frees, heap allocations or arbitrary memory writes.
It is not command injection, SQL Injection, Path Traversal, an unsafe sudo helper
or privilege escalation; the utility invokes no command, database, filename,
network or privilege API. Safe C pointer users, argument consumers without a
nullable-pointer operation, and callers checking NULL before use do not satisfy
this ground truth. An unconditional hardcoded NULL dereference also lacks this
fixture's meaningful input-dependent search.

### Firmware packaging and compilation

| Artifact | Firmware path |
| --- | --- |
| Vulnerable native C executable, root:root 0755 | `/usr/bin/fixture-device-info` |
| Corresponding source | `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c` |
| Diagnostic test executable, root:root 0755 | `/usr/share/iotbench/null-pointer-dereference/test-null-dereference` |
| Supporting assets, root:root 0644 | `test-null-dereference.c`, `test-guest.sh`, `ground-truth.json`, `NOTICE`, `LICENSE` in that same directory |

Records are compiled into the C executable, with no external metadata database.
The helper only compares names and prints artificial values. It opens no files,
contacts no service, reads no credentials, changes no configuration and requires
no root privilege. It installs no daemon, persistence, sudo rule or elevated file
permission. Existing device services/peripherals come from the unchanged profiles.

The package follows the existing `${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS}`
Yocto cross-compilation convention with `virtual/libc`; no external library or
new layer is needed. The vulnerable helper appends `-O0 -g -fno-inline -fno-lto`
to preserve the lookup call, nullable return and member loads. Package stripping
is inhibited so `lookup_record` and `records` remain recognizable. The normal
Yocto debug package handling still applies. The firmware executable has no
sanitizer runtime dependency. `busybox` and `util-linux-setpriv` support the
existing guest test convention. The pinned BusyBox configuration omits `timeout`,
so the existing C test supervisor supplies its own watchdog using `alarm()`.
All dependencies are supplied by pinned layers; the vulnerable utility itself
only needs libc.
Only this buffer-free helper also uses `-U_FORTIFY_SOURCE`: glibc's fortify
wrappers require optimization and otherwise reject the intentional `-O0` build
under `-Werror`. The other Yocto hardening flags remain in place; the diagnostic
supervisor uses the normal optimized flags and fortify setting.

`NOTICE`, image description, `/etc/motd` and helper stderr carry the exact
warning above. Source locations and records are also recorded in the installed
`ground-truth.json`. The image postprocess asserts ordinary 0755 helper ownership
and permissions. Recipes remain target-architecture independent.

### Build and static verification

Run these commands from the repository root:

~~~bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe476-null-pointer-dereference'
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe476-null-pointer-dereference.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

`--static` compiles a temporary copy with GCC `-fanalyzer` and requires one
`-Wanalyzer-null-dereference` diagnostic carrying CWE metadata 476 at line 43.
Its interprocedural diagnostic must include input line 38, lookup call/result
line 39, NULL return line 26 and sink line 43. It prints the diagnostic path and
checks machine-readable ground truth plus all eleven device recipes. A second,
temporary corrected control inserts a NULL check and must produce no CWE-476
finding. The installed vulnerable source is never modified by this test.

Offline image validation uses `debugfs` without mounting or executing firmware:

~~~bash
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/router-cwe476-null-pointer-dereference/qemuarm64/iotbench-router-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. It checks ELF architecture, preserved lookup symbols
and native call from `main`, both synthetic records, exact installed C sources,
metadata/test assets, ordinary file permissions, device identity and login warning.
For standard export filenames it also matches the installed device to the image
name, and compares the installed identity and peripheral files with that profile.
It prints the helper SHA-256. Disassembly inspection supports preservation of the
compiled flow; the GCC finding establishes the source-level defect. This is not
a claim that a binary-only analyzer independently recovered CWE-476.

The example `debugfs` path is for an aarch64 builder host, independent of target
architecture. Use `x86_64` on an x86_64 builder or `--debugfs debugfs` if on PATH.
Default target is `qemuarm64`; use `YOCTO_MACHINE` consistently for builds and
boots, and `--machine` plus a matching `--objdump` for offline inspection of
`qemuarm`, `qemux86-64`, `qemux86` or `qemumips`. The shared `scripts/build-all.sh`
automatically discovers every new image recipe.

### Optional isolated runtime verification

~~~bash
python3 scripts/test-null-pointer-dereference.py --device router
python3 scripts/test-null-pointer-dereference.py --all
# Optional acceleration on Apple Silicon, using unused device-service ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-null-pointer-dereference.py --all
~~~

Run separately from manual QEMU. The existing serial-console harness boots a
fresh snapshot, uses the existing `root` / `routeradmin` lab login only to run
tests, and shuts QEMU down in `finally`. Each export receives a raw
`validation-console.log`. The helper itself has no network surface.

Inside a manually booted guest, run `sh
/usr/share/iotbench/null-pointer-dereference/test-guest.sh router` on one line.
The five guest assertion groups check native installation, valid deterministic
`public` and `status` output, argument-count errors, the kernel-confirmed NULL
fault, and unprivileged execution with core dumps disabled. All helper processes
use UID/GID 65534 with cleared groups. The dedicated C test supervisor applies
a five-second watchdog and `RLIMIT_CORE=0` to each helper invocation. Its `--run`
mode forwards record arguments to the fixed executable and preserves its exit
status for valid-record and argument-count tests. With no arguments it forks the
fixed helper with `missing-record` and uses Linux `ptrace` to observe its actual
SIGSEGV. It requires `si_addr == NULL` and `si_code == SEGV_MAPERR`, forwards the
original kernel signal, then verifies signal termination. `PTRACE_O_EXITKILL`
also kills the traced child if the supervisor exits. The supervisor is test
infrastructure; it does not generate the fault or implement the vulnerability.

Expected valid output (stdout), with exit status 0:

~~~text
Record ID: 1
Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA
~~~

`status` prints ID 2 and `SYNTHETIC_STATUS_FIXTURE_DATA`. Missing/extra arguments
return 2 before accessing `argv[1]`. `missing-record` reaches C undefined behavior;
on the tested Linux target it should fault on `record->id` at address zero. The
supervisor's exact success marker is
`NULL_DEREFERENCE_CONFIRMED signal=SIGSEGV address=0 code=SEGV_MAPERR`.
A generic nonzero exit is insufficient. Other architectures or compiler settings
need independent verification; a missing ptrace facility is a runtime test
limitation, not a passing result. Static verification remains available.

### Safe remediation

A separate secure version must validate the nullable lookup result before use:

~~~c
const fixture_record_t *record = lookup_record(input);
if (record == NULL) {
    fprintf(stderr, "Record not found\n");
    return 1;
}
printf("Record ID: %d\n", record->id);
~~~

Whenever a pointer-returning function can return NULL, check that result before
accessing the referenced object. Keep ordinary argument validation as well.
Do not apply this correction to the intentionally vulnerable firmware fixture.

### Completed validation

On 2026-10-16, all eleven `qemuarm64` fixtures built and exported successfully
with the pinned Yocto builder after clean layer parsing and a router dependency
dry run. Both native C executables compiled with `-Wall -Wextra -Werror`.
Every exported manifest contains its correct device profile, `iotbench-sim`,
and exactly one vulnerability package: `cwe476-null-pointer-dereference`.

GCC's interprocedural `-fanalyzer` produced exactly one
`-Wanalyzer-null-dereference` finding with CWE metadata 476. Its diagnostic path
includes `argv[1]` at line 38, the lookup/assignment at line 39, the NULL return
at line 26, and the unchecked `record->id` at line 43. A temporary corrected
control with a NULL check produced no CWE-476 finding. The installed vulnerable
source was left unchanged.

Offline inspection passed for all eleven compressed ext4 images: target-native
ELF architecture, preserved lookup symbols and call from `main`, synthetic
record values, exact installed C sources/metadata/test assets, ordinary file
permissions, matching device identity/peripherals and required image warning.
The vulnerable helper is byte-identical across all eleven images, with SHA-256
`0e5198c3e75c26282926cc41d797501a783a1b34dd3a1a3a00a4502b8455aba8`.

All eleven images then booted as disposable QEMU snapshots with HVF/host CPU
and passed all five guest assertion groups, **55 groups total**. Valid records
returned their exact deterministic values; missing/extra arguments returned 2.
For `missing-record`, the supervisor observed kernel SIGSEGV at address zero
with `SEGV_MAPERR`, forwarded that signal and confirmed actual signal termination.
Every helper invocation ran as UID/GID 65534 with cleared groups, a five-second
watchdog and core dumps disabled. Guest regressions all returned zero. Tests
used the local serial console and existing host-loopback service ports HTTP
`18080`, MQTT `21883` and Modbus/TCP `11502`; the utility itself uses no network.

The [local validation report](../deploy-images/cwe476-validation/report.txt)
lists the generated repository files, every device's results, and SHA-256 checksums
for source files, compressed rootfs, kernel, manifest and validation logs.
Shared parse/static-analysis logs are under `deploy-images/cwe476-validation/`.
Each device export contains `build.log`, `rootfs.manifest`,
`validation-offline.log`, `validation-runtime.log` and `validation-console.log`.
Other supported architectures were not built or boot-tested. The static finding
comes from GCC source analysis; no independent binary-only CWE analyzer was run.

### doorlock-cwe476-null-pointer-dereference

Simulated category: **access-control door lock**. Existing device directory:
`meta-iotbench/recipes-devices/doorlock/`. Firmware directory:
`deploy-images/doorlock-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-doorlock-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-doorlock-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=doorlock-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/doorlock-cwe476-null-pointer-dereference/qemuarm64/iotbench-doorlock-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device doorlock
~~~

For manual boot use `FIRMWARE=doorlock-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh doorlock`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/doorlock-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### envsensor-cwe476-null-pointer-dereference

Simulated category: **environmental sensor**. Existing device directory:
`meta-iotbench/recipes-devices/envsensor/`. Firmware directory:
`deploy-images/envsensor-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-envsensor-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-envsensor-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=envsensor-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/envsensor-cwe476-null-pointer-dereference/qemuarm64/iotbench-envsensor-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device envsensor
~~~

For manual boot use `FIRMWARE=envsensor-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh envsensor`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/envsensor-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### healthmonitor-cwe476-null-pointer-dereference

Simulated category: **health monitor**. Existing device directory:
`meta-iotbench/recipes-devices/healthmonitor/`. Firmware directory:
`deploy-images/healthmonitor-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-healthmonitor-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-healthmonitor-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/healthmonitor-cwe476-null-pointer-dereference/qemuarm64/iotbench-healthmonitor-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device healthmonitor
~~~

For manual boot use `FIRMWARE=healthmonitor-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh healthmonitor`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/healthmonitor-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### ipcamera-cwe476-null-pointer-dereference

Simulated category: **surveillance IP camera**. Existing device directory:
`meta-iotbench/recipes-devices/ipcamera/`. Firmware directory:
`deploy-images/ipcamera-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-ipcamera-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-ipcamera-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/ipcamera-cwe476-null-pointer-dereference/qemuarm64/iotbench-ipcamera-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device ipcamera
~~~

For manual boot use `FIRMWARE=ipcamera-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh ipcamera`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/ipcamera-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### plc-cwe476-null-pointer-dereference

Simulated category: **industrial PLC gateway (OT)**. Existing device directory:
`meta-iotbench/recipes-devices/plc/`. Firmware directory:
`deploy-images/plc-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-plc-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-plc-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=plc-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/plc-cwe476-null-pointer-dereference/qemuarm64/iotbench-plc-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device plc
~~~

For manual boot use `FIRMWARE=plc-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh plc`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/plc-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### router-cwe476-null-pointer-dereference

Simulated category: **network gateway**. Existing device directory:
`meta-iotbench/recipes-devices/router/`. Firmware directory:
`deploy-images/router-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-router-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-router-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=router-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/router-cwe476-null-pointer-dereference/qemuarm64/iotbench-router-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device router
~~~

For manual boot use `FIRMWARE=router-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh router`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/router-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### smartbulb-cwe476-null-pointer-dereference

Simulated category: **lighting / smart bulb**. Existing device directory:
`meta-iotbench/recipes-devices/smartbulb/`. Firmware directory:
`deploy-images/smartbulb-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-smartbulb-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-smartbulb-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartbulb-cwe476-null-pointer-dereference/qemuarm64/iotbench-smartbulb-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device smartbulb
~~~

For manual boot use `FIRMWARE=smartbulb-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh smartbulb`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/smartbulb-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### smarthub-cwe476-null-pointer-dereference

Simulated category: **controller / smart hub**. Existing device directory:
`meta-iotbench/recipes-devices/smarthub/`. Firmware directory:
`deploy-images/smarthub-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-smarthub-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-smarthub-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=smarthub-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smarthub-cwe476-null-pointer-dereference/qemuarm64/iotbench-smarthub-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device smarthub
~~~

For manual boot use `FIRMWARE=smarthub-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh smarthub`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/smarthub-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### smartplug-cwe476-null-pointer-dereference

Simulated category: **energy-management smart plug**. Existing device directory:
`meta-iotbench/recipes-devices/smartplug/`. Firmware directory:
`deploy-images/smartplug-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-smartplug-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-smartplug-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=smartplug-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartplug-cwe476-null-pointer-dereference/qemuarm64/iotbench-smartplug-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device smartplug
~~~

For manual boot use `FIRMWARE=smartplug-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh smartplug`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/smartplug-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### smartspeaker-cwe476-null-pointer-dereference

Simulated category: **audio / voice-assistant speaker**. Existing device directory:
`meta-iotbench/recipes-devices/smartspeaker/`. Firmware directory:
`deploy-images/smartspeaker-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-smartspeaker-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-smartspeaker-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartspeaker-cwe476-null-pointer-dereference/qemuarm64/iotbench-smartspeaker-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device smartspeaker
~~~

For manual boot use `FIRMWARE=smartspeaker-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh smartspeaker`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/smartspeaker-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### thermostat-cwe476-null-pointer-dereference

Simulated category: **climate-control thermostat**. Existing device directory:
`meta-iotbench/recipes-devices/thermostat/`. Firmware directory:
`deploy-images/thermostat-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-thermostat-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-thermostat-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=thermostat-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/thermostat-cwe476-null-pointer-dereference/qemuarm64/iotbench-thermostat-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device thermostat
~~~

For manual boot use `FIRMWARE=thermostat-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh thermostat`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/thermostat-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

## Vulnerable C Binaries — Integer Overflow (CWE-190)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario and exact ground truth

Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Classification: **CWE-190: Integer Overflow or Wraparound**.
Every existing device category has one independent image combining its normal
profile with the sole vulnerability package `cwe190-integer-overflow`. The
local firmware utility estimates the size of a synthetic batch of telemetry
records. Its first command-line argument is the record count. It performs
only numeric conversion, multiplication, comparison and printing; no network,
filesystem access, allocation based on input, data copy, command execution,
configuration change, credential access or elevated privilege is needed.
The utility adds no daemon, boot service, login account, sudo grant or SUID bit.

The source is
[`fixture-batch-size.c`](../meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c).
It uses standard `<stdint.h>` types and `<inttypes.h>` portable conversion and
printing. `parse_record_count()` accepts only a nonempty string of ASCII digits,
converts with `strtoumax(..., 10)`, checks `ERANGE`, full consumption and the
`UINT32_MAX` bound, then assigns the validated value to `uint32_t record_count`.
Empty, signed, whitespace-bearing, hexadecimal, fractional, malformed and
out-of-range values return status 2 without numerical stdout. Decimal leading
zeroes are valid. Missing/extra arguments also return 2. Argument-count checking
short-circuits before accessing a nonexistent `argv[1]`.

These are **conversion bounds**, not multiplication bounds: valid input
`4194304` is accepted by the parser. All computations and decisions for valid
inputs return status 0, including ordinary capacity rejection. The final line
reports acceptance or rejection; exit status alone does not express capacity.

| Stage | Exact source location and operation |
| --- | --- |
| External numeric source | `main`, line 46: `argv[1]` passed to `parse_record_count` |
| Format and conversion validation | `parse_record_count`, lines 9–31; `strtoumax` at line 24; range test at line 25; validated assignment at line 28 |
| Fixed operands | Lines 41–42: `uint32_t record_size = 1024`, `uint32_t max_capacity = 4096` (both const) |
| Vulnerable arithmetic | `calculate_total`, line 35: `return record_count * record_size;` |
| Intentionally missing protection | Line 34 documents absent multiplication-bound validation; no sufficient check between parsed input and multiplication |
| Fixed-width destination | Line 51: `uint32_t total_size = calculate_total(record_count, record_size);` |
| Observable result | Lines 52–55 print count, size, stored total and capacity |
| Incorrect downstream logic | Line 56: `if (total_size <= max_capacity)`; lines 57–59 print the selected decision |

The multiplication uses 32-bit unsigned operands on all supported targets;
`calculate_total` returns `uint32_t`. No wider multiplication intermediate,
checked-arithmetic builtin, saturation, operation-bound input cap or overflow
rejection protects this path. The largest representable value is
**4294967295 (`UINT32_MAX`)**; results wrap modulo **4294967296 (2^32)**.
There is no dependency on undefined signed-integer overflow.

| Input | Exact mathematical total | Stored uint32_t total | Observed decision | Correct capacity decision |
| --- | --- | --- | --- | --- |
| `2` | 2048 | 2048 | accepted | accepted |
| `4` | 4096 | 4096 | accepted | accepted |
| `5` | 5120 | 5120 | exceeds capacity | exceeds capacity |
| `4194303` | 4294966272 | 4294966272 | exceeds capacity | exceeds capacity |
| `4194304` | 4294967296 | 0 | **accepted** | **exceeds capacity** |
| `4194305` | 4294968320 | 1024 | **accepted** | **exceeds capacity** |
| `4294967295` | 4398046510080 | 4294966272 | exceeds capacity | exceeds capacity |

Representative vulnerable flow, shared by every device:

`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → **incorrectly accepted**.

Expected static-analysis data flow: `argv[1]` → validated decimal conversion
→ `uint32_t record_count` → `calculate_total(record_count, record_size)`
→ unchecked 32-bit multiplication → `uint32_t total_size` → comparison with
4096 → printed synthetic decision. Expected finding: **CWE-190**, externally
controlled arithmetic can exceed the fixed-width destination without overflow
validation, and subsequent application logic consumes the incorrect result.
`ground-truth.json` records the exact lines, operands, label and witness.
The metadata labels are annotations; the arithmetic and its consumer must be
analyzed to establish the finding.

### Firmware components and compilation

| Artifact | Repository or installed location |
| --- | --- |
| Shared package recipe | `meta-iotbench/recipes-vulns/cwe190-integer-overflow/cwe190-integer-overflow_1.0.bb` |
| Actual native C source | `meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c` |
| Native executable, root:root 0755 | `/usr/bin/fixture-batch-size` |
| Identical installed source, root:root 0644 | `/usr/share/iotbench/integer-overflow/fixture-batch-size.c` |
| Matching annotation and local assets, root:root 0644 | `ground-truth.json`, `NOTICE`, `LICENSE`, `test-guest.sh` in that same data directory |
| Image metadata include | `meta-iotbench/recipes-images/iotbench-integer-overflow.inc` |
| Host validation runner | `scripts/test-integer-overflow.py` |

The recipe uses local `file://` sources, `S = "${UNPACKDIR}"`, `virtual/libc`,
and the normal `${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS}` cross compiler and flags.
It appends `-std=c99 -Wall -Wextra -Werror -O0 -g -fno-inline -fno-lto` to retain
the parser, arithmetic function, 32-bit multiplication and consumer for firmware
analysis. Package stripping is inhibited; normal Yocto debug-package handling
still applies. Only this buffer-free helper undefines `_FORTIFY_SOURCE`, matching
the existing native fixture convention because glibc fortify requires optimization
and otherwise fails the intentional `-O0 -Werror` build. Other Yocto hardening
flags remain. There is no sanitizer dependency in the firmware binary.

The helper uses only libc. BusyBox and `util-linux-setpriv` support guest tests;
the latter is ordinary non-SUID test infrastructure, never called by the utility.
No synthetic data file is needed: record size and capacity are fixed constants.
Device identity and peripheral configuration continue to come from each profile.
The image include verifies root-owned 0755 executable permissions and appends
NOTICE to `/etc/motd`. NOTICE, the image description and each utility invocation's
stderr display the exact warning above.

Recipes are architecture-independent and use the existing `YOCTO_MACHINE`
selector: default `qemuarm64`, or `qemuarm`, `qemux86-64`, `qemux86`, `qemumips`.
No architecture, toolchain or unrelated platform component is added. A source
shared by eleven images follows the existing device × vulnerability architecture;
each image contains its own installed native executable and corresponding source.
Exports contain the compressed ext4 rootfs and kernel in each firmware directory.
Build products under `deploy-images/` remain ignored by Git, following repository
policy; the package/image recipes and matching sources are the reproducible inputs.

### Local build and deterministic verification

Run host commands from the repository root. Parse the layer and resolve a graph:

~~~bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe190-integer-overflow'
~~~

Build and export all eleven fixtures with the existing exporter:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe190-integer-overflow.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

`scripts/build-all.sh` discovers these targets automatically. Use the same
`YOCTO_MACHINE` at build and boot time when selecting another supported target.

A separate local host build verifies exact numerical output and decisions using
Python's unlimited-precision arithmetic as the independent oracle. It covers
74 counts (ten chosen boundary/witness cases plus 64 deterministically seeded
counts), decimal leading-zero aliases, malformed strings, conversion overflow,
`UINT32_MAX`, and argument-count errors. It checks status and warning separately.

~~~bash
python3 scripts/test-integer-overflow.py --local
python3 scripts/test-integer-overflow.py --local --sanitize
~~~

`--cc` selects the host compiler. `--sanitize` additionally requires Clang
(`--clang` selects it), builds a temporary executable with
`-fsanitize=unsigned-integer-overflow -fno-sanitize-recover=unsigned-integer-overflow`,
and requires the specific **unsigned integer overflow: 4194304 * 1024** diagnostic
at source line 35. Input `2` must be clean. A separate temporary corrected control
adds the pre-multiplication bound check: normal input remains correct and the
overflow witness / maximum input return 2 with no diagnostic. Neither the
installed source nor the firmware binary is modified by these diagnostic tests.
Although the instrumentation is part of Clang's UBSan runtime, unsigned wraparound
is defined C behavior; its diagnostic does not imply signed undefined behavior.
These tests demonstrate a concrete arithmetic defect, not a generic failure.

Offline firmware inspection never mounts or executes the image:

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/router-cwe190-integer-overflow/qemuarm64/iotbench-router-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The `debugfs` path is for the aarch64 **builder host**; use the `x86_64` counterpart
on that host architecture, or `--debugfs debugfs` when on PATH. `--machine` selects
the expected target ELF class/endianness/machine; `--objdump` selects a matching
cross-objdump for other targets. The verifier checks parser and arithmetic calls
from native `main`, actual 32-bit multiplication in `calculate_total`, preserved
symbols, decision strings, lack of sanitizer instrumentation, exact installed
source/assets, device identity/peripherals, ordinary modes and the login warning.
It prints the helper SHA-256. Disassembly checks corroborate preservation of the
compiled flow; they are not an independent binary-only CWE-190 analyzer.

For manual testing, boot the selected firmware and use the existing guest serial
login `root` / `routeradmin`, then run **inside the guest**:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
setpriv --reuid=65534 --regid=65534 --clear-groups fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh router
~~~

Normal stdout is:

~~~text
record_count = 2
record_size = 1024
total_size = 2048
max_capacity = 4096
Synthetic batch accepted
~~~

Overflow stdout is:

~~~text
record_count = 4194304
record_size = 1024
total_size = 0
max_capacity = 4096
Synthetic batch accepted
~~~

Both commands return 0 with the warning on stderr. `fixture-batch-size 5`
returns 0 but reports `total_size = 5120` and `Synthetic batch exceeds capacity`.
The guest test checks six assertion groups: native installation/profile/modes;
normal arithmetic and decimal aliases; repeated exact overflow plus the incorrect
decision; arithmetic/capacity boundaries; format/range/count rejections; and
non-root execution. Every utility invocation runs as UID/GID 65534 with cleared
groups. It performs no file mutation or host access. Expected: six `PASS` lines,
exit 0. These bounded synthetic invocations terminate normally without a crash.

For automatic disposable QEMU boots, separately from manually running guests:

~~~bash
python3 scripts/test-integer-overflow.py --device router
python3 scripts/test-integer-overflow.py --all
# Optional Apple Silicon acceleration and unused existing service ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-integer-overflow.py --all
~~~

The host runner uses the existing serial-console/snapshot harness, runs one
image at a time, checks all six groups and status, closes QEMU in `finally`,
and saves `validation-console.log` beside the image. `--timeout` bounds each
console step. Profile service forwards are host-loopback-only; the calculator
itself does not use networking. Host QEMU and `zstd` are prerequisites.

### Safe remediation and distinctions

For a separate corrected variant, validate the operation's bounds before
multiplication and allow downstream logic to consume only a validated result:

~~~c
if (record_size != 0 && record_count > UINT32_MAX / record_size) {
    /* Reject an unrepresentable total before computing it. */
    return 2;
}
uint32_t total_size = record_count * record_size;
~~~

Appropriate checked-arithmetic functions are another option. A wider type is
sufficient for this calculation if multiplication is performed in that wider
type (for example `uint64_t`), the full result is validated and comparisons use
it without truncating it back to 32 bits. Merely assigning an already overflowed
32-bit product to a wider destination is insufficient. Keep robust parsing and
ordinary permissions. The corrected variant must preserve `2` → 2048, handle
capacity rejection correctly, and reject `4194304` or compare its full mathematical
total 4294967296 with capacity. The known-positive wraparound test must then fail.
These remediations are documented and used only in a temporary test control;
the intentionally vulnerable firmware path does not implement them.

These fixtures differ from generic Java/JAR applications and integer overflow
in unrelated apps: the input-to-arithmetic flow is in a real native C utility
built by Yocto and installed in each existing device firmware. They differ from
generic native C binaries, fixed-arithmetic programs and calculations that stay
within range: external numeric input reaches an actual 32-bit operation with a
reachable overflowing value and an observable incorrect result/decision. Numeric
input alone, arithmetic alone, a large representable value, or an unused label
is insufficient. Programs that correctly check arithmetic bounds do not satisfy
this ground truth.

They differ from integer underflow and signed conversion issues: input conversion
is checked, values are nonnegative, there is no subtraction, and the defect is
unsigned multiplication exceeding `UINT32_MAX`. They differ from buffer overflow,
heap/stack corruption, out-of-bounds access, NULL dereference and use-after-free:
the result controls no allocation, copy, pointer offset or index, and the program
has no dynamic allocation or free. They differ from command injection, SQL
Injection, Path Traversal and arbitrary command execution: the utility accepts
no commands, SQL or paths and invokes no process, database or file API. They
differ from generic application crashes: both witness inputs terminate normally;
the evidence is exact wraparound and a wrong simulated capacity decision.
The sole intended weakness is **CWE-190**.

The required relationship is **C binary input + input-dependent arithmetic +
fixed-width integer type + potential arithmetic overflow + missing overflow
validation + observable incorrect result**. Its harmless local consequence is
numerical misreporting and incorrect synthetic acceptance, without a secondary
memory-safety or privilege weakness.

### Completed validation

On 2026-10-16, all eleven `qemuarm64` fixtures built and exported successfully
with the pinned Yocto builder after clean BitBake layer parsing and a router
dependency dry run. The helper compiled with `-Wall -Wextra -Werror` and the
normal target toolchain. Every manifest contains the correct `device-<device>`,
`iotbench-sim`, and exactly one vulnerability package, `cwe190-integer-overflow`.

Host C builds passed on both macOS (Clang) and Linux in the existing builder
(GCC): each verified 74 exact numerical/result-decision cases, valid decimal
aliases, malformed/range/argument-count errors and deterministic exits.
The separate Clang unsigned-overflow diagnostic identified the exact multiplication
at line 35: `4194304 * 1024` cannot be represented by `uint32_t`. Normal input
and the temporary bounds-checked control had no such diagnostic. The firmware
source and binary retain their intentionally unchecked arithmetic.

Offline `debugfs` inspection passed for every exported compressed ext4 image:
aarch64 native ELF, calls from `main` to the input parser and arithmetic function,
actual **`mul w0, w1, w0`** 32-bit multiplication in `calculate_total`, both
decision strings, exact installed C source/assets/ground truth, ordinary root-owned
0755 helper and 0644 assets, correct device identity/peripherals, and required
NOTICE/login warning. Every image contains the same helper, SHA-256
`657d3f36f88ecd866bc07a59626f47176312b3ca5fa9b690bf48094be3942367`.

All eleven images booted as disposable QEMU snapshots with HVF/host CPU and
passed **six guest assertion groups each, 66 groups total**. Input `2` returned
2048 and accepted; `4194304` returned 0 and was incorrectly accepted, repeatedly.
The boundary and parsing tests also passed. All utility invocations ran as
UID/GID 65534 with cleared groups and ordinary permissions. Valid calculations
terminated with status 0, malformed input with status 2; no generic failure or
crash was used as overflow evidence. Tests used only the local serial console;
existing profile host-loopback ports were HTTP 18080, MQTT 21883 and Modbus 11502.
The calculator itself uses no network, unsafe memory operation or file access.

The [local validation report](../deploy-images/cwe190-validation/report.txt)
lists all generated repository files, each image's build/offline/runtime results,
all 66 guest assertion groups and SHA-256 checksums of sources, images, kernels,
manifests and logs. Shared logs are under `deploy-images/cwe190-validation/`.
Every device export contains `build.log`, `rootfs.manifest`,
`validation-offline.log`, `validation-runtime.log` and `validation-console.log`.

The existing `qemuarm`, `qemux86-64`, `qemux86` and `qemumips` targets were
**not built or boot-tested** in this run. Their recipes use the existing toolchain
selector without architecture-specific changes; no newly unsupported architecture
was identified. No independent binary-only CWE analyzer was run. The static
finding is expected ground truth supported by the source flow, actual native
multiplication, exact numerical behavior and separate unsigned-overflow diagnostic.

### doorlock-cwe190-integer-overflow

Simulated device category: **access-control door lock**, reusing
`meta-iotbench/recipes-devices/doorlock/`. Firmware directory:
`deploy-images/doorlock-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-doorlock-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-doorlock-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of lock telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=doorlock-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=doorlock-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh doorlock
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device doorlock
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/doorlock-cwe190-integer-overflow/qemuarm64/iotbench-doorlock-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/doorlock-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### envsensor-cwe190-integer-overflow

Simulated device category: **environmental sensor**, reusing
`meta-iotbench/recipes-devices/envsensor/`. Firmware directory:
`deploy-images/envsensor-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-envsensor-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-envsensor-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of environmental telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=envsensor-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=envsensor-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh envsensor
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device envsensor
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/envsensor-cwe190-integer-overflow/qemuarm64/iotbench-envsensor-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/envsensor-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### healthmonitor-cwe190-integer-overflow

Simulated device category: **health monitor**, reusing
`meta-iotbench/recipes-devices/healthmonitor/`. Firmware directory:
`deploy-images/healthmonitor-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-healthmonitor-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic health telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh healthmonitor
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device healthmonitor
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/healthmonitor-cwe190-integer-overflow/qemuarm64/iotbench-healthmonitor-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/healthmonitor-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### ipcamera-cwe190-integer-overflow

Simulated device category: **surveillance IP camera**, reusing
`meta-iotbench/recipes-devices/ipcamera/`. Firmware directory:
`deploy-images/ipcamera-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-ipcamera-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic snapshot metadata records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=ipcamera-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh ipcamera
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device ipcamera
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/ipcamera-cwe190-integer-overflow/qemuarm64/iotbench-ipcamera-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/ipcamera-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### plc-cwe190-integer-overflow

Simulated device category: **industrial PLC gateway (OT)**, reusing
`meta-iotbench/recipes-devices/plc/`. Firmware directory:
`deploy-images/plc-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-plc-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-plc-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic process telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=plc-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=plc-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh plc
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device plc
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/plc-cwe190-integer-overflow/qemuarm64/iotbench-plc-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/plc-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### router-cwe190-integer-overflow

Simulated device category: **network router / gateway**, reusing
`meta-iotbench/recipes-devices/router/`. Firmware directory:
`deploy-images/router-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-router-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-router-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic network telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=router-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=router-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh router
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device router
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/router-cwe190-integer-overflow/qemuarm64/iotbench-router-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/router-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### smartbulb-cwe190-integer-overflow

Simulated device category: **lighting / smart bulb**, reusing
`meta-iotbench/recipes-devices/smartbulb/`. Firmware directory:
`deploy-images/smartbulb-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-smartbulb-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic lighting telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=smartbulb-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh smartbulb
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device smartbulb
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartbulb-cwe190-integer-overflow/qemuarm64/iotbench-smartbulb-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/smartbulb-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### smarthub-cwe190-integer-overflow

Simulated device category: **controller / smart hub**, reusing
`meta-iotbench/recipes-devices/smarthub/`. Firmware directory:
`deploy-images/smarthub-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smarthub-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-smarthub-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic hub telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smarthub-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=smarthub-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh smarthub
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device smarthub
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smarthub-cwe190-integer-overflow/qemuarm64/iotbench-smarthub-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/smarthub-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### smartplug-cwe190-integer-overflow

Simulated device category: **energy-management smart plug**, reusing
`meta-iotbench/recipes-devices/smartplug/`. Firmware directory:
`deploy-images/smartplug-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartplug-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-smartplug-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic power telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartplug-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=smartplug-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh smartplug
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device smartplug
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartplug-cwe190-integer-overflow/qemuarm64/iotbench-smartplug-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/smartplug-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### smartspeaker-cwe190-integer-overflow

Simulated device category: **audio / voice-assistant speaker**, reusing
`meta-iotbench/recipes-devices/smartspeaker/`. Firmware directory:
`deploy-images/smartspeaker-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-smartspeaker-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic audio status records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh smartspeaker
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device smartspeaker
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartspeaker-cwe190-integer-overflow/qemuarm64/iotbench-smartspeaker-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/smartspeaker-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### thermostat-cwe190-integer-overflow

Simulated device category: **climate-control thermostat**, reusing
`meta-iotbench/recipes-devices/thermostat/`. Firmware directory:
`deploy-images/thermostat-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-thermostat-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-thermostat-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic climate telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=thermostat-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=thermostat-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh thermostat
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device thermostat
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/thermostat-cwe190-integer-overflow/qemuarm64/iotbench-thermostat-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/thermostat-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.
