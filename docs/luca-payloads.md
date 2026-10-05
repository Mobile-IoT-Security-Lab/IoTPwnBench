# Weak Cipher: 3DES Device Backups

These images implement intentionally vulnerable device backup encryption under
[CWE-327](https://cwe.mitre.org/data/definitions/327.html) (use of a broken or
risky cryptographic algorithm). The package directory is
`meta-iotbench/recipes-vulns/weak-cipher/`; its BitBake package is `cwe327-weak-cipher`.
The image IDs follow `<device>-cwe327-weak-cipher` for all eleven device profiles
listed in the root README. The recipes work with the existing architecture
selector and require no new layers or external source downloads.

## Scenario and scope

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

## Build and boot

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

## Dashboard and HTTP API

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

## Guest CLI and frame format

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

## Verification

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

# Permitted Root SSH Login (CWE-276)

The `cwe276-permit-root-login` module intentionally permits direct SSH login
as `root` using a password. Image IDs follow
`<device>-cwe276-permit-root-login` for all eleven device profiles. Evaluate
the scenario through the effective SSH configuration, an actual login attempt
and the privileges obtained. Source inspection alone does not confirm that a
running firmware accepts the login; the commands below are a verification
procedure, not a record of completed runtime tests.

## Configuration and security implications

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

## Build and boot

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

## Verify the effective configuration

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

## Verify login and privileges without changing the guest

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

## Exposure and severity

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

## Remediation and verification

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

# Allow anonymous login (CWE-276)

## Scenario and CWE mapping

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

## Package and runtime behavior

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

## Build and boot

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

## Payloads and expected results

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

## Regression and guest inspection

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

### Connection refused: check the host control port

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

### Inspect the guest service

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

## Completed validation

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

## Remediation and verification

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
