# Luca Payloads

This guide documents the Luca firmware scenarios and their reproducible lab
payloads. See [Hardcoded credentials (CWE-798)](#hardcoded-credentials-cwe-798)
for the shared vendor support account on all eleven devices.

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
