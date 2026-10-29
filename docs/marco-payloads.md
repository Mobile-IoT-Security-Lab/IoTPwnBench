# 🧪 Marco Payloads

Technical reference for Marco's **15 fixture families**. For the practical
checklist in Italian, use the [Testing Guide](../../audit-marco-2026-10-27/guida-test-marco.md).
Read the common setup once, choose a family, then expand its reference only as needed.

<a id="how-to-use-this-guide"></a>
<a id="common-setup"></a>

## 🚦 Common setup — read once

### Where commands run

- **Host / PC**: the Linux terminal at the repository root, beside `compose.yaml` and `scripts/`.
- **Guest**: the firmware's serial console after QEMU starts. Guest commands are labelled explicitly.
- On **TRUX01**, use **`/usr/bin/python3`** for host Python commands: it is Python 3.9; plain `python3` is Python 3.6.
- Use a normal user for host tests. Some isolated runners reject host root.

### What you need

| Task | Requirements |
| --- | --- |
| Local checks | Python plus the tools required by that family; see the Testing Guide. |
| Firmware build | Docker daemon access and Docker Compose. Prepare the builder once. |
| Direct host boot | Matching QEMU binary and `zstd`. |
| Manual Docker boot | `scripts/run-qemu-docker.sh` uses QEMU from the existing `yocto-build` volume; build the selected firmware first. |

On TRUX01, the host QEMU and `zstd` commands are absent as of **2026-10-27**.
The Docker launcher is available for manual boots; automated runners that invoke
host QEMU still need their own prerequisites.

Prepare the Docker builder once, before the first firmware build:

```bash
docker compose build yocto
```

### How to read results

**PASS / OK + exit 0** means the checks that ran behaved as expected.
**SKIP** means a check did not run. **FAIL / ERROR** requires investigation.
Run `echo "exit=$?"` immediately after the command whose status you need.

A passing vulnerability test confirms the expected benchmark behavior.
Record **local test**, **firmware build**, and **firmware verification** separately.
Source checks do not prove that a generated image works.

<a id="device-keywords"></a>

### 🧭 Device keywords

Use the exact keyword below. These eleven profiles are shared by all families;
device-specific services and metadata may differ.

| Device type | Keyword |
| --- | --- |
| Router | `router` |
| IP camera | `ipcamera` |
| Smart plug | `smartplug` |
| Thermostat | `thermostat` |
| Programmable logic controller | `plc` |
| Smart bulb | `smartbulb` |
| Smart home hub | `smarthub` |
| Environmental sensor | `envsensor` |
| Smart speaker | `smartspeaker` |
| Health monitor | `healthmonitor` |
| Door lock | `doorlock` |

<a id="build-and-boot-any-device"></a>

### Firmware naming, build and boot

Firmware ID: **`<device>-<scenario>`**. The default machine is `qemuarm64`;
use the same `YOCTO_MACHINE` for build and boot. Exports are under
`deploy-images/<firmware>/<machine>/`.

The original common example is the SSH configuration fixture:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe521-permit-empty-passwords
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

**Other families have their own opt-in requirements** in the existing reference
below. This example does not enable them. Boot is optional for SSH policy checks.

Run one firmware at a time. A browser is relevant only when that image exposes
an HTTP interface; serial-only fixtures have no dashboard. To quit QEMU:
**Ctrl-A**, release, then **X**. Default guest writes are disposable.

<a id="manual-test-index"></a>

## 🗂️ Family index

All families below support the eleven device profiles. Variant counts describe
separate scenarios, not additional devices.

| Family | Variants per device | Scope |
| --- | --- | --- |
| [SSH policy](#weakly-configured-ssh--empty-password-authentication-permitted-cwe-521) | 1 | Configuration only; no SSH login test. |
| [FTP write permissions](#weakly-configured-vsftpd-bad-write-rights) | 1 | File permissions and the read-only control. |
| [Telnet traffic](#weakly-configured-telnet--unencrypted-traffic-cwe-798287276) | 1 | Synthetic plaintext sessions and capture evidence. |
| [Sudo environment](#bad-sudo-rights--allow-changes-to-environment-variables-cwe-798) | 1 | Environment policy and the diagnostic helper. |
| [Cron wildcard](#cronjob-wildcard-injection-cwe-8878269) | 1 | Argument handling in a synthetic maintenance task. |
| [Password leak](#password-leak--different-file-types-and-patterns-cwe-798) | 15 | Credential representations in synthetic files. |
| [REST internal files](#exploitable-rest-interface--internal-files-cwe-22cwe-73) | 1 | File-access boundaries in a local fixture. |
| [Embedded credentials](#embedded-credential-pairs-over-a-unix-socket-cwe-798) | 8 | Synthetic authentication pairs and artifact checks. |
| [Apache applications](#apache-application-fixtures-ten-cwes-eleven-devices) | 10 | Application fixtures, including browser-dependent checks. |
| [C path / filename](#native-c-path-fixtures-cwe-22-and-cwe-20) | 2 | Path handling and filename-policy controls. |
| [C buffer overflow](#native-c-buffer-overflow-cwe-787-cwe-20-cwe-119) | 1 | Memory-safety diagnostics and the corrected control. |
| [C connection string](#native-connection-string-injection-cwe-20) | 1 | Connection-option validation and the corrected control. |
| [C symbolic links](#native-c-symbolic-link-following-cwe-61-and-cwe-59) | 1 | Symbolic-link boundaries and the corrected control. |
| [Java command handling](#java-jar-command-injection-cwe-78--cwe-77-contributing-cwe-20) | 2 | Two synthetic command-handling variants. |
| [Java deserialization](#java-deserialization-cwe-502-with-cwe-20-contributing) | 1 | Type validation and callback evidence. |

**Validation dates in the references are historical implementation records.**
This editorial revision does not execute the tests or establish new results.

<a id="technical-references"></a>

### 📎 Technical references

- [OpenSSH configuration manual](https://man.openbsd.org/sshd_config#PermitEmptyPasswords).
- [CWE-521: Weak Password Requirements](https://cwe.mitre.org/data/definitions/521.html).

## 📚 Family references

Expand a family for its original procedure, source locations, controls and
validation limits. Payloads and scenario-specific test commands are preserved.

<a id="weakly-configured-ssh--empty-password-authentication-permitted-cwe-521"></a>

## 🔐 SSH policy

Configuration only; no SSH login test.

<details>
<summary>Procedure and technical details</summary>

**Weakly Configured SSH — Empty Password Authentication Permitted (CWE-521)**

### Build, boot and manual testing

**What this tests.** The SSH configuration explicitly permits empty-password
authentication by policy. The positive case must report
`permitemptypasswords yes`; a copy differing only in that directive must report
`permitemptypasswords no`. Both must be syntactically valid. The same procedure
applies to all eleven devices.

**Build:** use the [common SSH example](#build-and-boot-any-device).
Boot is optional. The checks below run on the host in configuration-test mode.

**Test — host, inspect the configuration:**

```bash
cat meta-iotbench/recipes-vulns/cwe521-permit-empty-passwords/files/sshd_config
```

Expected: the file contains `PermitEmptyPasswords yes`,
`PasswordAuthentication yes` and `PermitRootLogin no`.

**Prepare isolated test files — host:**

```bash
work_dir=$(mktemp -d)
SSHD_BIN=/usr/sbin/sshd

cp meta-iotbench/recipes-vulns/cwe521-permit-empty-passwords/files/sshd_config \
   "$work_dir/positive.conf"
ssh-keygen -q -t ed25519 -N '' -f "$work_dir/host_key"
```

Set `SSHD_BIN` to the absolute path of a compatible native OpenSSH server if it
is installed elsewhere. The generated key is temporary test material and is
never installed on the host as a service key or included in the firmware.

**Positive case — host, syntax validation:**

```bash
"$SSHD_BIN" -t -f "$work_dir/positive.conf" -h "$work_dir/host_key"
echo "exit=$?"
```

Expected: no diagnostic from `sshd -t`, followed by `exit=0`. A diagnostic or
nonzero exit is a failed check; resolve the reported host-tooling or
configuration issue before interpreting the result.

**Positive case — host, effective policy:**

```bash
"$SSHD_BIN" -T -f "$work_dir/positive.conf" -h "$work_dir/host_key" |
  grep -E '^(permitemptypasswords|passwordauthentication|permitrootlogin) '
```

Expected, in any order:

```text
permitrootlogin no
passwordauthentication yes
permitemptypasswords yes
```

**Negative control — host:**

```bash
sed 's/^PermitEmptyPasswords yes$/PermitEmptyPasswords no/' \
  "$work_dir/positive.conf" > "$work_dir/negative.conf"

"$SSHD_BIN" -t -f "$work_dir/negative.conf" -h "$work_dir/host_key"
echo "exit=$?"

"$SSHD_BIN" -T -f "$work_dir/negative.conf" -h "$work_dir/host_key" |
  grep -E '^(permitemptypasswords|passwordauthentication|permitrootlogin) '
```

Expected: syntax validation returns `exit=0`; effective configuration reports
`permitemptypasswords no`, while `passwordauthentication yes` and
`permitrootlogin no` remain unchanged. The empty-password policy finding must
be absent from this negative control.

**Check a generated firmware — host:** the commands above inspect the source
configuration. To verify the artifact, follow
[Inspect the generated firmware](#inspect-the-generated-firmware), then copy its
configuration into the positive case and repeat the positive and negative
checks in the same terminal:

```bash
cp "$inspection_dir/rootfs/etc/ssh/sshd_config" "$work_dir/positive.conf"
```

**Cleanup — host:** after completing both cases:

```bash
rm -r "$work_dir"
```

Only the temporary test directory is removed. Neither `sshd -t` nor `sshd -T`
starts a listening server or attempts authentication.

### Positive and negative test cases

| Case | Input | Expected result |
| --- | --- | --- |
| Positive | Shipped `sshd_config`: `PermitEmptyPasswords yes` | Policy finding present; effective `permitemptypasswords yes` |
| Negative control | Temporary copy with only `PermitEmptyPasswords no` | No empty-password policy finding; effective `permitemptypasswords no` |
| Ambiguous or unrelated change | Duplicate directive, `Include`, `Match`, root login enabled, or password authentication disabled | Fixture validation fails |
| Invalid isolation | Missing configuration, SSH daemon/startup entry, or empty account password field | Rootfs validation fails |

### Scenario and expected finding

Affected component: OpenSSH server configuration at `/etc/ssh/sshd_config`.
Every listed image installs the same regular, mode-0644 configuration file:

```text
PermitEmptyPasswords yes
PasswordAuthentication yes
PermitRootLogin no
```

`PermitEmptyPasswords yes` is the sole intentional policy misconfiguration.
Password authentication is enabled so that the empty-password setting is
meaningful as a policy; root login remains prohibited. The standalone
configuration contains no `Include` or `Match` blocks and sets other policy
controls explicitly: strict file checks, no host-based authentication, no
user-supplied environment, and no agent/TCP/X11/tunnel forwarding. Loopback-only
`ListenAddress` is an additional precaution, not the service isolation mechanism.

Expected static result: identify the explicit insecure directive in the SSH
server configuration and associate it with the risk of accepting empty-password
authentication. CWE-521 describes the weak password policy; this fixture does
not contain an actual empty password credential.

The OpenSSH option permits empty-password login only when suitable accounts
exist and other authentication/access rules allow it. It neither creates such
accounts nor guarantees successful authentication. Here there is no operational
SSH authentication path and no login demonstration.

### Packaging and isolation

- Module: `meta-iotbench/recipes-vulns/cwe521-permit-empty-passwords/`.
- Installed payload: only `/etc/ssh/sshd_config`; no server, private keys,
  users, credentials, init scripts, systemd units or persistence hooks.
- Opt-in: eleven `iotbench-<device>-cwe521-permit-empty-passwords.bb` recipes
  require `iotbench-permit-empty-passwords.inc`. Shared image defaults, device
  profiles and other vulnerability images do not enable the package.
- The include excludes `openssh-sshd` and `dropbear` and fails rootfs validation
  if known SSH server binaries or startup entries are present. Configuration
  alone cannot listen on TCP or UDP. No QEMU SSH forwarding was introduced.
- These images remove password-relaxing development features (`debug-tweaks`,
  `allow-empty-password`, `empty-root-password`, `allow-root-login`) inherited
  from local build configuration. This does not affect other image recipes.
- No authentication database changes are introduced. The existing common
  benchmark serial-console setup remains inherited from `iotbench-image.inc`.
  This fixture does not add or reuse credentials for a remote SSH service.

This repository contains synthetic benchmark images, not a production image
family. The new package is selected only through explicit fixture recipes and
is absent from the common image configuration. A downstream production build
must not select this synthetic package/include; that downstream build is outside
this repository's validation scope.

### Inspect the generated firmware

The common fixture include attaches an offline rootfs validation hook to
`do_rootfs`. A successful build must contain the expected configuration, no
recognized SSH server binary/startup entry, and no empty password field in
`/etc/passwd` or `/etc/shadow`. The hook reads those databases without changing
them. The same hook runs for each of the eleven image recipes.

An existing extracted generated rootfs can also be checked from the host:

```bash
python3 scripts/test-ssh-empty-passwords.py --rootfs /absolute/path/to/extracted-rootfs
```

This option requires a complete rootfs, including its authentication databases.
Do not point it at a live host filesystem. To inspect the exported ext4 without
booting it, use host `zstd` and `debugfs` (from e2fsprogs):

```bash
TEST_MACHINE=${YOCTO_MACHINE:-qemuarm64}
inspection_dir=$(mktemp -d /tmp/iotbench-ssh-inspect.XXXXXX)
mkdir "$inspection_dir/rootfs"
zstd -dc "deploy-images/$TEST_FIRMWARE/$TEST_MACHINE/iotbench-$TEST_FIRMWARE-$TEST_MACHINE.rootfs.ext4.zst" > "$inspection_dir/image.ext4"
debugfs -R "rdump / $inspection_dir/rootfs" "$inspection_dir/image.ext4"
python3 scripts/test-ssh-empty-passwords.py --rootfs "$inspection_dir/rootfs"
```

`debugfs` opens the image read only by default. Inspect any extraction errors;
a partial extraction cannot establish the properties of the complete image.
No boot is needed. If booting to inspect device functionality, the existing
`FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh` command adds only the existing
device services; this scenario does not match any SSH port-forwarding case.

### Automated configuration validation

```bash
# Portable policy, negative-control, isolation and source integration tests:
python3 scripts/test-ssh-empty-passwords.py --skip-openssh

# Also run native OpenSSH syntax/effective checks when available:
python3 scripts/test-ssh-empty-passwords.py

# Select a compatible native OpenSSH explicitly:
python3 scripts/test-ssh-empty-passwords.py --sshd /usr/sbin/sshd
```

Positive and negative controls differ by exactly the empty-password directive.
The validator returns a finding for `yes` and no finding for `no`; an unexpected
policy or an unsupported directive fails validation instead of yielding a false
negative. It is intentionally a closed fixture-policy checker, not a general
OpenSSH configuration analyzer.

For OpenSSH checks the runner generates an ephemeral host key in a temporary
directory, passes an explicit configuration path, and executes only `sshd -t`
and `sshd -T`. Both controls must pass syntax checks; effective policy must report
`permitemptypasswords yes`/`no`, `passwordauthentication yes`, and
`permitrootlogin no`. Keys are never installed in firmware. Tests never start a
server, open a listening socket, modify system configuration, or attempt login.

Missing tooling produces an explicit SKIP. If a discovered/specified binary
fails validation, the test fails with its diagnostic; it does not report a pass.
Host compatibility problems can be separated from portable checks with
`--skip-openssh`.

### Executed validation and limitations

Executed during implementation:

- Portable positive/negative tests, rejection cases and staged rootfs safeguards: PASS.
- Source integration checks for all eleven devices and exclusion from other
  image/configuration sources: PASS.
- Native OpenSSH 8.4p1: `sshd -t` and `sshd -T` for both controls: PASS.

The staged rootfs used by self-tests is temporary test data, not a built Yocto
image. Docker daemon access was denied in the implementation environment, so
BitBake parsing, package builds, generated-rootfs checks and boot tests were
not executed. Their success is not implied by the source-level checks. Run the
build and `--rootfs` instructions above to verify a generated artifact.

The fixture's single-variable policy is the only newly introduced weakness;
shared synthetic-device behavior is inherited. Static tools may distinguish a
configuration finding from exploitable SSH exposure because no daemon exists.
The rootfs checks cover known server/startup names, not arbitrary renamed code
or unrelated device-service vulnerabilities. No successful empty-password login
is expected or required.

</details>

<a id="weakly-configured-vsftpd-bad-write-rights"></a>

## 📁 FTP write permissions

File permissions and the read-only control.

<details>
<summary>Procedure and technical details</summary>

**Weakly configured vsftpd: bad write rights**

Scenario keyword: `cwe276-bad-write-rights`. All eleven device keywords above
have an image recipe at
`meta-iotbench/recipes-images/iotbench-<device>-cwe276-bad-write-rights.bb`.
The shared implementation is
`meta-iotbench/recipes-vulns/cwe276-bad-write-rights/`; image safeguards live in
`meta-iotbench/recipes-images/iotbench-bad-write-rights.inc`.

This fixture has **one intentional defect, CWE-276 (incorrect default
permissions)**: `/srv/iotbench-ftp/bad` is owned by `root:ftpfixture` with mode
`0775`, although the intended maintenance policy permits listing and downloading
only. The authenticated account `ftpfixture` belongs to that group, so
`write_enable=YES` lets it upload ordinary files. The neighboring
`/srv/iotbench-ftp/control` has the same ownership and content but mode `0755`;
its upload must fail. The FTP root is root-owned `0755`, and both `readme.txt`
files are root-owned `0644`. No executable content, payload execution or
privilege escalation is part of this scenario.

CWE-434 describes the related ability to upload files where policy forbids it;
CWE-287 is an authentication review category, **not an additional authentication
vulnerability** here. Authentication remains mandatory. The synthetic account
has shell `/bin/false` and a reproducible SHA-512 password hash. Its test-only
password is `Fixture-FTP-Only-42`; it grants access only to disposable fixture
data. This credential is public benchmark input, not a production secret.

Installed configuration is `/etc/iotbench/vsftpd-write-rights.conf`, with PAM
policy `/etc/pam.d/iotbench-ftp` and the single-account allowlist
`/etc/iotbench/ftp-users`. PAM uses `pam_unix`, anonymous access is disabled,
root is absent from the allowlist, and local users are chrooted to
`/srv/iotbench-ftp`. Active FTP, SITE commands, directory changes, renames and
permission changes are disabled; passive transfer ports are 30100–30109.
`STOR bad/probe.txt` is the ordinary test write.

### Build and automated validation

Run these commands from the repository root. Build tools and their pinned
sources must already be available in the existing Yocto cache for an offline
build. Functional validation itself uses no external network.

```bash
# Portable source/configuration checks; no Docker, root or daemon required.
python3 scripts/check-ftp-write-rights.py

# Explicit test-build opt-in, applies only to this scenario.
FIRMWARE=router-cwe276-bad-write-rights docker compose run --rm \
  -e IOTBENCH_ENABLE_FTP_WRITE_FIXTURE=1 yocto

# Boot the exported image in a disposable QEMU snapshot and test on its console.
python3 scripts/test-ftp-write-rights.py --device router

# Automated build/export/boot/test for all eleven categories.
python3 scripts/test-ftp-write-rights.py --all --build
```

The opt-in wrapper supplies a temporary BitBake configuration selecting PAM,
systemd and vsftpd's PAM support. It removes that configuration on exit and
does not change persistent build configuration. Building a fixture image without
`IOTBENCH_ENABLE_FTP_WRITE_FIXTURE = "1"` fails before rootfs creation. Generic
`scripts/build-all.sh` skips these guarded fixtures unless called with
`IOTBENCH_ENABLE_FTP_WRITE_FIXTURE=1`; use the explicit test build above to
build and validate this scenario. `YOCTO_MACHINE` selects the build architecture and must
match the existing QEMU runner's selection.

For a manual guest run, boot the selected image using `scripts/run-qemu.sh`, log
in on the serial console as `root` / `routeradmin`, then run:

```bash
python3 /usr/share/iotbench/bad-write-rights/test-guest.py --isolated-fixture
```

Expected five PASS results cover mandatory authentication (including anonymous,
root and wrong-password rejection), listing/download, unauthorized upload in
`bad` versus rejection in `control`, blocked outside-root reads, and permission
inspection plus the repaired-directory control. The test confirms that the
uploaded file belongs to the unprivileged account. It temporarily changes `bad`
to `0755` and verifies that upload then fails. A `finally` block stops the
service, deletes probe files, restores the original fixture permissions and
removes the runtime opt-in marker. The host runner destroys its QEMU snapshot;
it saves console output under `/tmp/iotbench-ftp-<device>-qemu.log`. Abrupt guest
power loss bypasses in-guest cleanup; discard the snapshot in that case.

Machine-readable policy is installed at
`/usr/share/iotbench/bad-write-rights/policy.json`.
Static analysis should correlate `write_enable=YES`, authenticated user/group
membership and `root:ftpfixture 0775` on `bad` against the read-only policy in
this section and the packaged `readme.txt`. It should distinguish the `0755`
control and avoid reporting anonymous upload or root FTP login. Source checks
verify recipe coverage and declared settings; they do not replace inspecting
an exported rootfs or running vsftpd in the guest.

### Isolation and limitations

`iotbench-ftp-write.service` has no boot enablement and requires
`/run/iotbench-ftp-write-test`, created only during the explicit guest test.
The upstream `vsftpd.service` and `vsftpd.socket` are masked in these images.
The fixture binds `127.0.0.1:2121` **inside a systemd private network namespace**;
the guest test uses `nsenter` to run its local FTP client in that namespace.
Neither control nor data ports are forwarded to the host. A strict systemd
filesystem sandbox permits writes only to the two synthetic directories; Unix
permissions distinguish the vulnerable case from its control.

Upstream vsftpd requires a root authentication/chroot broker for local-account
login. That broker is limited to SETUID, SETGID and SYS_CHROOT capabilities;
authenticated FTP sessions and uploaded files use the unprivileged account.
Thus this implementation does **not** provide a daemon with no privileged
process at all. A strict requirement forbidding even the broker is not met;
upstream's unprivileged launching-user mode cannot provide this local-login
model. No FTP operation is intended to execute with root file privileges, and
the guest ownership assertion checks the upload identity.

These are opt-in synthetic images, not a production deployment mechanism.
The build guard prevents accidental inclusion through these image targets; it
cannot prevent someone deliberately repackaging the source or bypassing the
guard. Existing shared device services and serial-console credentials retain
the repository's baseline behavior. FTP is plaintext only inside the private
namespace. The runtime requires Linux namespaces, systemd, PAM, vsftpd and the
existing guest/QEMU toolchain. Build and runtime success must be established on
a host with Docker daemon access; source validation alone is insufficient.

Validation on 2026-10-23: offline integration/configuration checks passed for
all eleven profiles, as did Python syntax, shell syntax and whitespace checks.
The Docker daemon denied access even outside the filesystem sandbox; no
firmware image was available for the attempted guest test. BitBake builds,
rootfs inspection and functional FTP results therefore remain unverified.
The broker limitation is grounded in [vsftpd's local-login implementation](https://github.com/InfrastructureServices/vsftpd/blob/master/oneprocess.c),
which does not accept authenticated local logins in its unprivileged one-process mode.

</details>

<a id="weakly-configured-telnet--unencrypted-traffic-cwe-798287276"></a>

## 📡 Telnet traffic

Synthetic plaintext sessions and capture evidence.

<details>
<summary>Procedure and technical details</summary>

**Weakly Configured Telnet – Unencrypted Traffic (CWE-798/287/276)**

### Scenario and source locations

Each of the eleven device keywords above has a separate
`<device>-cwe798-unencrypted-traffic` image. These images install **one intentional
scenario**, a weakly configured synthetic Telnet service. CWE-798, CWE-287 and
CWE-276 describe related characteristics of that service. The plaintext
transport is observable alongside those characteristics; this fixture does not
install an actual Telnet login daemon or alter OS accounts.

The shared package and source are
`meta-iotbench/recipes-vulns/cwe798-unencrypted-traffic/`, with image recipes at
`meta-iotbench/recipes-images/iotbench-<device>-cwe798-unencrypted-traffic.bb` and
shared image integration in `iotbench-unencrypted-traffic.inc`.

| Installed location | Role / expected finding |
| --- | --- |
| `/usr/bin/fixture-telnet` | Rendered `files/fixture-telnet.py`; hard-coded synthetic credentials and `authenticated()` ignoring the asserted username in password-only mode |
| `/etc/iotbench/telnet-auth.json` | Authentication mode `password-only`; intentionally `root:root 0666`, allowing ordinary local users to change the service's authentication policy; intended policy-file permissions are `0644` |
| `/usr/share/iotbench/unencrypted-traffic/build-config.json` | Required test-only build manifest, mode `fixture`, enabled `true`, supported QEMU machine |
| `/usr/share/iotbench/unencrypted-traffic/ground-truth.json` | Machine-readable scenario, credentials, source symbols, CWEs and permissions |
| `/usr/share/iotbench/unencrypted-traffic/` | Original service/build source, notice, license and automated `test-session.py` |
| systemd unit `iotbench-telnet.service` | Disabled manual test unit; private network namespace, unprivileged account, read-only filesystem sandbox |

Unit files use Yocto's `${systemd_system_unitdir}`. No unit enablement hook or
`[Install]` section is supplied. Image postprocessing verifies the installed
policy's `root:root 0666` metadata and helper's ordinary `root:root 0755` metadata.

### Authentication and plaintext data flow

The public synthetic username is **`telnet-fixture`**, and its public synthetic
password is **`Fixture-Telnet-Only-42`**. These are benchmark inputs, never real
accounts or secrets. Both values are constants in the service source (CWE-798).
The client sends the username after `login: ` and the password after `Password: `,
using unencrypted TCP/NVT lines. No TLS, key exchange, credential hashing on the
wire or operating-system authentication is performed.

`authenticated()` deliberately accepts **any nonempty claimed username** when
the password matches the fixed synthetic password. Thus
`unlisted-synthetic-user` with that password succeeds too (CWE-287). Empty names
and incorrect passwords fail. This is confined to the same synthetic service;
no account impersonation or OS login results. A temporary
`username-and-password` policy control in the automated test rejects the wrong
username while accepting the expected one, then restores the fixture policy.

The mode `0666` policy models CWE-276 on the authentication configuration
itself. Its only functional field selects the weak or strict identity check.
Its fields cannot select a bind address, executable, file path or command.
A temporary mode `0644` permission control removes group/other write access;
the tests restore `0666` afterward. The systemd sandbox additionally makes
configuration read-only within the service's mount namespace. Static tools
should still report the underlying image file's permissive mode.

After authentication, `STATUS` returns `SYNTHETIC STATUS: nominal`, `HELP`
lists `STATUS HELP QUIT`, and `QUIT` returns `Goodbye fixture` and closes the
session. Every other input returns `Unknown synthetic command`. Inputs such as
`id` and `/bin/sh` are tested as inert text. The handler never invokes a shell,
subprocess, filesystem command or privileged operation.

### Host builds and automated local tests

Source/configuration inspection needs Python 3 and no network:

```bash
python3 scripts/test-telnet-unencrypted-traffic.py --static
```

It checks all eleven device recipes, the source's credential and authentication
conditions, unit isolation, ground truth and positive/negative build-policy
cases. It executes the actual recipe Python guard bodies against minimal
metadata stubs; this offline check does not parse BitBake or build a firmware.

The dedicated **host test build**, independent of Yocto, uses the same staging
implementation as the firmware recipe:

```bash
python3 scripts/build-telnet-fixture.py --output /tmp/iotbench-telnet-build \
  --mode fixture --enable 1 --machine qemuarm64
```

Omitting either opt-in, selecting `--mode production`, or selecting a machine
outside the supported QEMU list fails before writing fixture files. The
generated helper also refuses to start without `--fixture-test` or with a
missing/production/disabled/unsupported-machine build manifest.

The automated local test builds a fresh temporary fixture, starts only finite
loopback listeners, performs the synthetic sessions and removes its build:

```bash
python3 scripts/test-telnet-unencrypted-traffic.py --local --isolated-fixture \
  --transcript /tmp/iotbench-telnet-wire.json
```

This Linux test requires no external service or DNS. It checks successful
synthetic authentication, incorrect passwords and empty usernames, deliberate
wrong-username acceptance, strict identity and permission controls, malformed
and oversized input, NVT CRLF/CR-NUL, option refusal, and fixed command
responses. It rejects startup without the runtime opt-in or with production
metadata. Connections to the machine's **own assigned non-loopback IPv4
addresses** must return connection refused; no probe targets another host.
It also checks that the listener refuses `127.0.0.2` and offers no `--host`
override. If no non-loopback IPv4 address exists, that probe is explicitly
reported as skipped. The service has no IPv6 socket.

For actual packet capture without host root privileges, run in a rootless
Linux user/network namespace containing only loopback (requires `unshare`,
`ip`, and enabled unprivileged user namespaces):

```bash
unshare --user --map-root-user --net /bin/bash -c '
  ip link set lo up &&
  exec python3 scripts/test-telnet-unencrypted-traffic.py \
    --local --isolated-fixture --require-pcap \
    --pcap /tmp/iotbench-telnet-isolated.pcap \
    --transcript /tmp/iotbench-telnet-isolated-wire.json
'
tcpdump -nn -A -r /tmp/iotbench-telnet-isolated.pcap
```

The namespace has no external connectivity. The service runs as the caller's
unprivileged host identity; namespace UID 0 does not grant host root access.
Because this namespace has only loopback, the external-interface probe is
skipped here; the ordinary local run above covers assigned host interfaces.
When run as real guest root, the test keeps capture in its parent and drops
the service subprocess to `nobody`.

The capture records actual Linux loopback Ethernet/IP/TCP frames and filters
them to the fixture ports. It checks payloads for the username, password,
`STATUS` and `SYNTHETIC STATUS: nominal` without decryption. The PCAP can be
opened in Wireshark and followed as a TCP stream; ephemeral test ports vary.
The service default port is `2323`. Packet timestamps, TCP sequence numbers,
port numbers and segmentation vary; the expected protocol results are fixed.
The JSON transcript records the bytes actually sent/received by the client;
it is a socket transcript, not a packet capture. Without raw-socket capability,
the default run reports a capture skip and writes no PCAP. `--require-pcap`
turns that limitation into a failure.

### Firmware build and guest validation

Build and boot one device (replace `router` with any listed device keyword):

```bash
FIRMWARE=router-cwe798-unencrypted-traffic docker compose run --rm \
  -e IOTBENCH_ENABLE_TELNET_FIXTURE=1 yocto
FIRMWARE=router-cwe798-unencrypted-traffic ./scripts/run-qemu.sh
```

The container wrapper passes a temporary BitBake configuration with
`IOTBENCH_BUILD_MODE = "fixture"`, `IOTBENCH_ENABLE_TELNET_FIXTURE = "1"` and
systemd enabled. It rejects the flag for other image families or an explicit
production-mode environment setting. The package provider is skipped unless
both global settings and a supported QEMU machine are selected. An additional
image rootfs guard enforces the same policy. The package install task rechecks
the policy, and its signature includes the opt-ins and machine. Default and
production configurations cannot resolve/install this fixture through the
provided recipes, including after a prior fixture build populated sstate.

For a direct BitBake test build, put those two settings plus
`INIT_MANAGER = "systemd"` in a dedicated test config and pass it with `-r`.
Supported machines are `qemuarm64`, `qemuarm`, `qemux86-64`, `qemux86` and
`qemumips`. `scripts/build-all.sh` skips this family by default; set
`IOTBENCH_ENABLE_TELNET_FIXTURE=1` to include it. No Telnet forwarding is added
to `run-qemu.sh`.

After the usual guest console login, execute the packaged automated test:

```bash
python3 /usr/share/iotbench/unencrypted-traffic/test-session.py \
  --installed --isolated-fixture --require-pcap \
  --pcap /tmp/iotbench-telnet.pcap --transcript /tmp/iotbench-telnet-wire.json
```

It executes the installed helper, restores the original policy, manifest and
permissions in a `finally` block, and terminates every child process. Run in a
disposable QEMU snapshot, as abrupt termination can bypass cleanup. This direct
test uses the guest's loopback; it does not start the systemd unit. For separate
manual unit inspection, create `/run/iotbench-telnet-test`, then manually start
`iotbench-telnet.service`. Its listener is additionally hidden in a private
network namespace; a client/capture must enter that namespace to observe it.
Stop the unit and remove the marker after testing. Neither the marker nor any
startup link is included in the firmware.

An extracted, trusted fixture rootfs can be inspected without executing it:

```bash
python3 scripts/test-telnet-unencrypted-traffic.py --rootfs /path/to/extracted-rootfs
```

This checks the installed helper, fixture manifest, authentication policy and
permissions, assets, disabled unit and absence of a preinstalled runtime marker.
It supplements the build-time owner/mode checks; inspecting staged host data
does not establish that a Yocto firmware was successfully built.

### Safeguards, findings and validation status

Static findings should correlate the hard-coded credentials with the plaintext
login prompts, password-only authentication sink and mode `0666` policy. Dynamic
findings should show accepted ordinary login, rejected incorrect passwords,
accepted unlisted usernames with the fixture password, and readable credential
and status bytes in locally captured TCP payloads. The strict-identity control
rejects the unlisted user; mode `0644` removes ordinary-user policy writes.

The fixed IPv4 loopback address and accepted peer are checked in code, outside
the writable policy. One process handles one session, with a 30-second process
limit, 10-second accept timeout, bounded input and command count. The optional
unit adds a private network namespace, `nobody` identity, empty capabilities,
no-new-privileges, read-only filesystem and no restart. There is no OS shell,
privilege escalation, remote access facility or persistent boot service.
This is a bounded Telnet-compatible NVT subset, not a full terminal emulator;
clients must use the three uppercase synthetic commands. Unsupported Telnet
options, including START-TLS, are refused.

The build/runtime gates prevent accidental use through this benchmark's
configurations. They do not prevent deliberate source modification, forged
fixture metadata or repackaging into another build. The repository's baseline
device services and console credentials remain in their existing profiles;
only this new Telnet scenario is added to each image.

Validation on **2026-10-23**: source integration and offline recipe guards
passed for all eleven devices and all five supported QEMU machine values.
Host dynamic sessions passed, including actual assigned-interface connection
refusals. A separate rootless namespace run passed **required real packet
capture**; `tcpdump` independently decoded the PCAP containing the synthetic
username, password and status text. Python/shell syntax and whitespace checks
passed. The attempted Docker firmware build failed because the current user
cannot access the Docker daemon socket, so actual BitBake builds, exported
rootfs checks and guest/systemd execution remain unverified.

</details>

<a id="bad-sudo-rights--allow-changes-to-environment-variables-cwe-798"></a>

## 🛡️ Sudo environment

Environment policy and the diagnostic helper.

<details>
<summary>Procedure and technical details</summary>

**Bad SUDO Rights – Allow Changes to Environment Variables (CWE-798)**

### Scenario, device matrix and source locations

One shared fixture implements a local sudo workflow in each of the eleven
supported device categories. The new image installs exactly one intentional
scenario: a dedicated low-privileged account can influence selected environment
settings consumed by a root diagnostic helper. A hard-coded public diagnostic
credential represents **CWE-798: Use of Hard-coded Credentials** within this same
workflow. Environment preservation alone is not CWE-798; tooling should report
the insecure environment policy and the fixed credential as distinct evidence
of this scenario. There is no loader injection or privileged code execution
payload, and this does not reuse the existing LD_PRELOAD or sudo path-traversal
fixtures.

| Device category | Firmware ID |
| --- | --- |
| Door lock | `doorlock-cwe798-sudo-environment` |
| Environmental sensor | `envsensor-cwe798-sudo-environment` |
| Health monitor | `healthmonitor-cwe798-sudo-environment` |
| IP camera | `ipcamera-cwe798-sudo-environment` |
| PLC | `plc-cwe798-sudo-environment` |
| Router | `router-cwe798-sudo-environment` |
| Smart bulb | `smartbulb-cwe798-sudo-environment` |
| Smart hub | `smarthub-cwe798-sudo-environment` |
| Smart plug | `smartplug-cwe798-sudo-environment` |
| Smart speaker | `smartspeaker-cwe798-sudo-environment` |
| Thermostat | `thermostat-cwe798-sudo-environment` |

The shared package is
`meta-iotbench/recipes-vulns/cwe798-sudo-environment/cwe798-sudo-environment_1.0.bb`.
Its `files/` directory contains the native C source `fixture-sudo-env.c`, sudoers
template `iotbench-sudo-environment`, shared `fixture-build.py`, automated
`test-session.py`, `ground-truth.json`, notice and MIT license. Each image recipe
is `meta-iotbench/recipes-images/iotbench-<firmware-id>.bb`, requiring the existing
common image/device profile and the new `iotbench-sudo-environment.inc`.

| Installed location | Purpose / metadata |
| --- | --- |
| `/usr/bin/fixture-sudo-env` | Native helper, ordinary `root:root 0755`; no setuid bit |
| `/etc/sudoers.d/iotbench-sudo-environment` | Test-only policy, `root:root 0440` |
| `/usr/share/iotbench/sudo-environment/build-config` | Fixed runtime test-build marker, `root:root 0644` |
| `/usr/share/iotbench/sudo-environment/` | C/build source, rendered automated test, ground truth, license and notice |

### Sudo rule, credentials and environment data flow

The dedicated account is **`fixtureenv`**, UID/GID **989**, home `/nonexistent`,
shell `/bin/false` and locked OS password `!`. It has no SSH/login credential.
A root test harness drops its subprocess to that identity, which invokes
`sudo -n /usr/bin/fixture-sudo-env --fixture-test`. The test-only policy is:

```sudoers
Defaults:fixtureenv env_reset, !setenv
Defaults:fixtureenv env_keep = "FIXTURE_MODE FIXTURE_CONFIG TEST_PROFILE"
Defaults:fixtureenv !env_check
Defaults:fixtureenv secure_path = "/usr/bin:/bin"
fixtureenv ALL=(root) NOPASSWD: NOSETENV: /usr/bin/fixture-sudo-env --fixture-test
```

`ALL` occupies the host field; the permitted command and arguments are exact.
No wildcard command or runas permission is granted. `NOPASSWD` avoids storing an
OS password and applies only to this one harmless helper invocation.
`NOSETENV` and `!setenv` retain restrictions on `-E` and command-line variable
assignments. `env_reset` remains enabled. The list-valued `!env_check` removes
the usual additional caller-variable preservation exceptions for this account;
sudo still creates its standard identity, path and `SUDO_*` metadata variables.
The allowlist refers to caller-controlled fixture variables, not to every
variable sudo generates. These semantics follow the
[upstream sudoers environment and tag definitions](https://github.com/sudo-project/sudo/blob/main/docs/sudoers.man.in).

The intentional policy defect is `env_keep`: a low-privileged caller can change
the diagnostic mode, profile and synthetic credential used by the privileged
helper. `getenv()` reads the three settings; bounded fixed-string comparisons
select predefined output. Nothing is evaluated as a command or opened as a
path. In particular, `FIXTURE_CONFIG` is an enum/credential input, not a filename.

| Variable | Default | Other accepted value / behavior |
| --- | --- | --- |
| `FIXTURE_MODE` | `status` | `diagnostic`, requiring the fixed synthetic credential |
| `FIXTURE_CONFIG` | `public` | `Fixture-Sudo-Only-42`, compared against C constant `FIXTURE_PASSWORD` |
| `TEST_PROFILE` | `baseline` | `boundary`, visible in fixed diagnostic output |

**`Fixture-Sudo-Only-42` is public synthetic benchmark data.** It unlocks only
`RESULT=synthetic-diagnostic` in this helper, authenticates to no OS account or
real service, and is never a production credential. It is deliberately present
in C source and the compiled fixture binary for CWE-798 analysis. Incorrect or
path-like credentials return status 3. Invalid modes/profiles return status 2.
Values are not reflected into errors. The helper reads only its fixed public
build manifest; it has no shell, subprocess, socket, arbitrary file-read,
dynamic-library load or system-configuration mutation API.

Default successful output is exactly:

```text
FIXTURE_EUID=0
MODE=status
CONFIG=public
PROFILE=baseline
UNLISTED=absent
RESULT=nominal
```

Setting only `TEST_PROFILE=boundary` changes only `PROFILE=boundary`. Setting
all three permitted variables to `diagnostic`, the public credential, and
`boundary` gives `MODE=diagnostic`, `CONFIG=synthetic-fixed`, `PROFILE=boundary`
and `RESULT=synthetic-diagnostic`, still with EUID 0 and `UNLISTED=absent`.
The credential itself is not echoed. Both inherited settings and explicit sudo
assignments are tested. The inert `FIXTURE_UNLISTED` witness reports only
`present`/`absent`: direct root helper execution can observe it, while sudo
removes inherited instances and rejects command-line assignments.

### Dedicated builds and offline/native tests

From the repository root, run the source/policy/build-gate checks:

```bash
python3 scripts/test-sudo-env-fixture.py --static
```

This checks all eleven device recipes, exact sudo rule scope, source-level
environment/credential evidence, helper API restrictions, and native `visudo`
syntax without installing any host policy. It executes the actual recipe Python
guard bodies with minimal metadata stubs across all five supported QEMU machines
and invalid production/disabled/missing/non-QEMU combinations. This is an offline
guard check, not a BitBake parse or firmware build.

The dedicated native test build uses the same staging code as Yocto:

```bash
python3 scripts/build-sudo-env-fixture.py --output /tmp/iotbench-sudo-env-build \
  --mode fixture --enable 1 --machine qemuarm64
python3 scripts/test-sudo-env-fixture.py --local --isolated-fixture
```

The output must be a fresh staging directory. It remains beneath `/tmp` and
does not install a host sudoers fragment. The staged helper has a compiled fixed
manifest path in that directory. The native tests compile/run a fresh helper
inside a rootless single-user and network namespace, verify all fixed responses
and invalid inputs, and test missing, malformed, production, disabled, symlinked
and writable manifests. They verify that compilation without the fixture macro
refuses all requests and omits the fixed credential. These tests require Linux
user/network namespaces, a C compiler, `nm` and Python 3.6 or later. Namespace
UID 0 has no host root authority. This mode tests C behavior only; it cannot
model a second user for real sudo in its single-user namespace.

For an automated **actual sudo-policy test**, use the disposable VM runner on
an x86_64 Debian-style Linux host with QEMU, BusyBox, system Python, sudo/PAM and
a readable x86 Linux kernel supporting initramfs:

```bash
python3 scripts/test-sudo-env-vm.py --isolated-fixture \
  --kernel /boot/vmlinuz-<installed-version> \
  --log /tmp/iotbench-sudo-env-vm.log
```

Optional `--qemu /path/to/qemu-system-x86_64` and `--bios-dir /path/to/seabios`
select an unpacked local toolchain. No package download occurs in the runner.
It compiles/stages the fixture with target paths, creates a temporary initramfs
with root ownership represented in archive metadata, and boots under TCG.
Only trusted host binaries/libraries are copied; accounts, shadow entries,
sudo policy and PAM files are generated from public synthetic inputs. The
minimal VM grants only the scoped fixture rule, locks both account passwords,
and uses `pam_deny` for authentication with permitted account/session checks.
It runs the same packaged `test-session.py` as the firmware and powers off.
There is no virtual NIC, host filesystem mount or persistent disk. Temporary
build artifacts are deleted; the serial log remains. CPIO member order,
ownership and timestamps are fixed; host toolchain versions and boot timing
are not pinned by this convenience runner. The fixture has no external-network
dependency, and all expected protocol/output assertions are deterministic.

### Firmware build, guest tests and production exclusion

```bash
FIRMWARE=router-cwe798-sudo-environment docker compose run --rm \
  -e IOTBENCH_ENABLE_SUDO_ENV_FIXTURE=1 yocto
FIRMWARE=router-cwe798-sudo-environment ./scripts/run-qemu.sh
```

Substitute any firmware ID in the table. Supported machines are `qemuarm64`,
`qemuarm`, `qemux86-64`, `qemux86` and `qemumips`; select one with `YOCTO_MACHINE`.
The container wrapper writes a temporary BitBake test configuration with
`IOTBENCH_BUILD_MODE = "fixture"` and `IOTBENCH_ENABLE_SUDO_ENV_FIXTURE = "1"`.
It rejects explicit production mode, a different image family, or simultaneous
Telnet/FTP fixture opt-ins. Direct BitBake builds require those two global
settings in a dedicated test configuration supplied with `-r`.
`scripts/build-all.sh` skips this family unless
`IOTBENCH_ENABLE_SUDO_ENV_FIXTURE=1` is set.

The package provider is skipped by default and in production configurations,
including when previously built fixture packages exist in caches. The install
task rechecks the opt-ins and machine before staging anything, task signatures
include the gate variables, and the image rootfs task enforces the same policy.
Rootfs postprocessing checks helper/policy/manifest owner and mode and the
standard sudoers include directory. The default system sudo policy and other
accounts' environment handling are untouched. No service or startup hook is
installed. The C helper additionally requires compile-time fixture enablement,
the exact `--fixture-test` argument, EUID 0, and a root-owned regular manifest
with exact fixture contents and no group/other write access; failures return 77.

After the repository's usual guest console login in a disposable QEMU snapshot:

```bash
python3 /usr/share/iotbench/sudo-environment/test-session.py \
  --installed --isolated-fixture
```

The test drops subprocesses to UID/GID 989 using real OS credentials and executes
the installed setuid sudo and configured rule. It verifies default output,
inherited and explicitly assigned allowlist values, incorrect credentials,
unlisted-variable removal, rejected unlisted/loader/path assignments and `-E`,
root EUID in the helper, and denied shells/other commands/runas identities/extra
arguments. A root-only **fake** production-credential canary proves that direct
and sudo-mediated private-file access are unavailable. No real credentials are
read or supplied. Every subprocess has a timeout and closed standard input.
The manifest is temporarily altered for negative tests and restored in `finally`;
abrupt termination can bypass restoration, so always use a disposable snapshot.

Inspect an extracted trusted rootfs without executing guest binaries:

```bash
python3 scripts/test-sudo-env-fixture.py --rootfs /path/to/extracted-rootfs
```

This checks modes, exact policy, build marker, packaged artifacts, compiled
credential and absence of fixture startup links. Build postprocessing and guest
tests additionally check root ownership, which host extraction may not preserve.

### Expected findings, safeguards and validation limits

Static tools should identify `env_keep` for `fixtureenv`, its precise runas/
command/argument scope, and data flow from the three preserved `getenv` inputs
into the fixed diagnostic choices. CWE-798 evidence is the constant
`FIXTURE_PASSWORD`, its presence in the ELF, and its comparison with
`FIXTURE_CONFIG`. Dynamic tools should see EUID 0, changed predefined output for
permitted settings, and removal/rejection of outside settings. Unsupported input
must never reach a command executor, loader or file-selection sink.

The safeguards prevent accidental production inclusion through these recipes;
they cannot prevent someone deliberately modifying the source or repackaging
the fixture. Existing baseline device services and console credentials remain
as defined by the repository. The public diagnostic credential is not an
additional OS account weakness. The VM test validates the shared native helper
and actual sudo semantics but does not establish cross-compilation or complete
device-image behavior on every architecture.

Validation on **2026-10-23**: offline source/integration/guard checks passed for
all eleven device profiles and all five supported QEMU machine settings; native
`visudo` accepted the policy. Native C tests passed in a rootless network/user
namespace, including default, boundary, invalid-input and production-build
controls. The **real sudo** test passed under QEMU 5.2 TCG with Linux
5.10.0-33-amd64 and Debian sudo 1.9.5p2, with all six guest assertion groups and
`IOTBENCH_SUDO_ENV_EXIT=0`; serial evidence is
`/tmp/iotbench-sudo-env-vm.log`. The firmware build was attempted but Docker
daemon access was denied even outside the filesystem sandbox. Actual BitBake
parsing/builds, exported firmware rootfs inspection and device-image guest tests
therefore remain unverified.

Shell/Python/JSON syntax and whitespace checks passed. Tests with stubbed
BitBake/Docker commands verified wrapper configuration selection/cleanup,
production/wrong-family/mixed-opt-in rejection, and default catalog exclusion
of all eleven images. The rootfs checker accepted a native staged target tree
and rejected a substituted unrestricted rule; this is not evidence of an
exported Yocto image.

</details>

<a id="cronjob-wildcard-injection-cwe-8878269"></a>

## ⏰ Cron wildcard

Argument handling in a synthetic maintenance task.

<details>
<summary>Procedure and technical details</summary>

**Cronjob Wildcard Injection (CWE-88/78/269)**

### Scenario and source integration

**Vulnerable Cronjob Configurations – Cronjob Wildcard Injection** has one
intentional defect: the scheduled maintenance command expands a bare `*` over
lower-privileged filenames without separating options from file operands.
**CWE-88** is the primary argument-injection label. **CWE-78** and **CWE-269**
describe the associated command and privileged-maintenance boundaries in this
model. This fixture implements neither arbitrary command execution nor an
actual privilege transition; related labels describe the same single scenario.
The secure crontab is a negative control for that scenario.

The shared package and sources are under
`meta-iotbench/recipes-vulns/cwe088-cronjob-wildcard-injection/`:

| Source | Purpose |
| --- | --- |
| `cwe088-cronjob-wildcard-injection_1.0.bb` | Native cross-compilation, locked user, dedicated-tree installation, production guard |
| `files/fixture-maintenance.c` | Diagnostic-only native argument parser and fixed runtime-context checks |
| `files/vulnerable.crontab.in`, `files/secure.crontab.in` | Inert schedules, differing only by the argument separator |
| `files/fixture-runner.py` | Fixed-command validation and deterministic wildcard-to-argv expansion |
| `files/fixture-build.py` | Shared build policy, native compilation and target staging |
| `files/ground-truth.json`, `files/NOTICE` | Analysis labels, data flow, boundaries and test-only notice |

`meta-iotbench/recipes-images/iotbench-cronjob-wildcard-injection.inc` selects
exactly this vulnerability package, checks fixture mode before rootfs creation,
and checks installed ownership/modes. Every image requires the existing common
image, its own device profile, and this shared include. Firmware recipes are
`meta-iotbench/recipes-images/iotbench-<firmware-id>.bb`:

| Device | Firmware ID |
| --- | --- |
| Door lock | `doorlock-cwe088-cronjob-wildcard-injection` |
| Environmental sensor | `envsensor-cwe088-cronjob-wildcard-injection` |
| Health monitor | `healthmonitor-cwe088-cronjob-wildcard-injection` |
| IP camera | `ipcamera-cwe088-cronjob-wildcard-injection` |
| PLC | `plc-cwe088-cronjob-wildcard-injection` |
| Router | `router-cwe088-cronjob-wildcard-injection` |
| Smart bulb | `smartbulb-cwe088-cronjob-wildcard-injection` |
| Smart hub | `smarthub-cwe088-cronjob-wildcard-injection` |
| Smart plug | `smartplug-cwe088-cronjob-wildcard-injection` |
| Smart speaker | `smartspeaker-cwe088-cronjob-wildcard-injection` |
| Thermostat | `thermostat-cwe088-cronjob-wildcard-injection` |

### Files, schedule and filename control

All scenario artifacts stay under the fixture root
`/usr/share/iotbench/cronjob-wildcard-injection/` in target images. Native staging
uses the same suffix under the chosen disposable output directory.

| Relative path | Permissions and role in firmware |
| --- | --- |
| `inbox/` | `fixturefiles:fixturefiles 0750`; lower-privileged filename-control boundary |
| `inbox/alpha.record`, `inbox/beta.record` | `fixturefiles:fixturefiles 0644`; harmless starting operands |
| `bin/fixture-maintenance` | `root:root 0755`; ordinary ELF with no setuid/setgid bits |
| `cron/vulnerable.crontab`, `cron/secure.crontab` | `root:root 0644`; inert test schedules |
| `build-config` | `root:root 0644`; exact fixture-only runtime marker |
| `logs/` | `root:root 0755`; new `vulnerable.jsonl` / `secure.jsonl` files are mode `0600` |
| `source/`, `fixture-runner.py`, ground truth and notices | Root-owned build/configuration evidence and manual test runner |

The locked synthetic user `fixturefiles`, UID/GID **988**, has no home directory,
a locked password and `/bin/false` as its shell. Ownership lets it create or
rename files inside `inbox/`; it cannot replace root-owned controls, the helper
or logs. No world-writable directory or relaxed system security configuration
is introduced. Native tests model this role in a temporary tree owned by the
invoking user; they do not create host accounts or claim to verify OS UID
separation.

Rendered vulnerable schedule, with `ROOT` standing for the fixture root:

```text
*/5 * * * * root cd ROOT/inbox && ROOT/bin/fixture-maintenance --fixture-test *
```

This declares maintenance every five minutes. The `root` field represents a
**simulated privileged role**. The runner validates the schedule and command,
then executes it once immediately; it neither waits for the wall clock nor
changes UID. Nothing is installed in `/etc/cron*` or a system crontab spool,
and no cron daemon, service, timer, sudo rule or startup hook is added.
Never copy the test definitions to a real scheduler.

The intended data flow is:

```text
fixturefiles creates/renames inbox/--fixture-diagnostic
  -> cd into the dedicated inbox
  -> bare * yields the basename --fixture-diagnostic
  -> argv enters fixture-maintenance.c
  -> option branch before the -- separator
  -> predefined synthetic-diagnostic output
```

An absolute-path wildcard or `./*` would prefix the basename and avoid this
particular option-prefix condition. The fixture deliberately uses bare `*`.
The secure schedule is the identical command with **`--fixture-test -- *`**.
Its `--` disables option interpretation for every subsequent argument.
Harmless test names include `alpha.record`, `beta.record`,
`--fixture-diagnostic`, `--unknown`, and `-q`. Unknown options are reported as
options but cause no action. Only the exact `--fixture-diagnostic` spelling
selects the fixed alternate output.

### Build and run locally

Requirements: Python 3.6 or later, a native C11 `cc`, POSIX shell for build
wrappers, and `nm` for regression inspection. Everything runs offline without
root or a real cron daemon. From the repository root:

```bash
python3 scripts/test-cron-wildcard-fixture.py --isolated-fixture
```

The test creates and cleans its own temporary staging trees. For a reviewable
manual native build, use a new empty output directory:

```bash
CRON_STAGE=$(mktemp -d /tmp/iotbench-cron.XXXXXX)
python3 scripts/build-cron-wildcard-fixture.py --output "$CRON_STAGE" \
  --mode fixture --enable 1 --machine qemuarm64
CRON_ROOT="$CRON_STAGE/usr/share/iotbench/cronjob-wildcard-injection"
python3 "$CRON_ROOT/fixture-runner.py" --root "$CRON_ROOT" --isolated-fixture
```

The first run reports two operands, zero options and `nominal`. Introduce the
boundary filename and remove only the previous fixture diagnostic log:

```bash
python3 - "$CRON_ROOT" <<'PYFIXTURE'
from pathlib import Path
import sys
root = Path(sys.argv[1])
(root / 'inbox/--fixture-diagnostic').write_text('synthetic filename only\n')
(root / 'logs/vulnerable.jsonl').unlink()
PYFIXTURE
python3 "$CRON_ROOT/fixture-runner.py" --root "$CRON_ROOT" --isolated-fixture
python3 "$CRON_ROOT/fixture-runner.py" --root "$CRON_ROOT" --isolated-fixture --secure
```

The vulnerable run includes:

```json
{"kind":"option","argument":"--fixture-diagnostic"}
{"options":1,"operands":2,"result":"synthetic-diagnostic"}
```

The secure run includes:

```json
{"kind":"separator"}
{"kind":"operand","argument":"--fixture-diagnostic"}
{"options":0,"operands":3,"result":"nominal"}
```

Both also report `simulated-privileged-maintenance` and
`actual_privilege_change: false`. The helper exits 0 after valid diagnostic
processing. Missing test arguments, incorrect cwd, a missing/modified/symlinked
marker, or a helper compiled without enablement return 77. The runner refuses
altered commands and existing log files, including symlinks, rather than
replacing them. For a repeat run, explicitly remove the corresponding log
inside this disposable fixture tree. Delete the disposable `CRON_STAGE` tree
when finished.

### Firmware build integration

Docker Compose/Yocto are required for cross-built firmware. Select any device
ID in the table; for example:

```bash
FIRMWARE=router-cwe088-cronjob-wildcard-injection docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture \
  -e IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE=1 yocto
```

Export destination:
`deploy-images/<device>-cwe088-cronjob-wildcard-injection/<machine>/`.
Supported machine settings are `qemuarm64`, `qemuarm`, `qemux86-64`, `qemux86`
and `qemumips`. Set `YOCTO_MACHINE` on the host to select a different one.
The catalog builder skips these eleven images by default; setting
`IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE=1` includes them. It forwards explicit
fixture mode to the container. Normal `scripts/build-all.sh` also builds the
other catalog scenarios.

The container wrapper uses a temporary BitBake configuration and removes it on
exit. It rejects production mode, another scenario's image, and mixed fixture
opt-ins. Package parsing and the image rootfs guard independently reject
`IOTBENCH_BUILD_MODE=production`, missing opt-in or a non-QEMU machine. Native
staging enforces the same policy before writing or compiling. The C source
requires `IOTBENCH_CRON_WILDCARD_FIXTURE_ENABLED=1`; an ordinary production
compilation contains only a refusal stub. The enabled helper additionally checks
the exact runtime marker and the designated inbox cwd. These controls prevent
production enablement through the provided build paths; deliberate source
modification or repackaging is outside the model.

For a manual run in a disposable fixture guest, invoke the installed Python
runner with `--isolated-fixture`. It defaults to its own fixture directory and
executes with the caller's existing UID. The commands and expected diagnostics
above apply with `CRON_ROOT=/usr/share/iotbench/cronjob-wildcard-injection`.
The native regression harness runs on the host, not inside the image.

### Analysis expectations, safeguards and validation limits

Static/configuration analysis should connect the lower-privileged inbox owner,
`cd` and bare wildcard in the root-role schedule, absence of `--`, and the C
parser's `argv[i][0] == '-'` condition. The sink changes only counters and a
fixed diagnostic label. Configuration inspection should distinguish the secure
separator control. The source and ground truth are packaged for this purpose;
no third-party static analyzer result is claimed.

The runner emulates this fixed command's argv expansion using a sorted inbox
listing, excluding dotfiles and retaining literal `*` when nothing matches.
It validates the full command with `shlex` and uses `subprocess` with a fixed
executable and argv; it never executes shell source. Filename metacharacters
remain literal data. The helper opens only its fixed build marker, never file
operands or symlink targets, and prints JSON diagnostics. It executes no external
commands, changes no privileges, writes no files and has no network APIs.
Only the runner writes new logs under the fixture root.

The regression covers ordinary names, creation and rename of option-like names,
the secure separator, unknown options, a filename literally named `--`, empty
and hidden inputs, nested/outside-directory exclusion, unreadable operands and
symlinked synthetic canaries, shell metacharacters, malformed configuration,
protected controls and log links, runtime-context refusal, production compilation,
all eleven device integrations, build-gate combinations for all five machines,
target-path staging, and wrapper opt-in/configuration cleanup using local stubs.
The control tests confirm that outside files do not supply argv or get modified.

Known limits: this is a deterministic one-shot schedule/role simulation, not a
test of a real daemon, shell, privilege escalation, user switching, concurrent
rename races, or production maintenance software. Local ownership checks are
mode/configuration checks; guest UID enforcement remains unverified until a
firmware build and guest test are run. Non-ASCII filename bytes are JSON-escaped
byte by byte. Existing baseline device services and console settings come from
the repository's shared image/device profiles.

Validation on **2026-10-23**: all **11 native/source/integration test groups
passed**, including the actual recipe Python guards under mocked BitBake
metadata and stubbed build-wrapper checks. Python/JSON and shell syntax checks
and `git diff --check` passed. Docker daemon access was denied both within and outside the filesystem
sandbox; actual BitBake parsing, cross-compilation, exported-rootfs ownership
checks and device-image guest execution could not be performed here. Passing
native tests and mocked wrapper/recipe checks do not establish those results.

</details>

<a id="password-leak--different-file-types-and-patterns-cwe-798"></a>

## 🔑 Password leak

Credential representations in synthetic files.

<details>
<summary>Procedure and technical details</summary>

**Password Leak – Different File Types and Patterns (CWE-798)**

This family models **CWE-798, Use of Hard-coded Credentials**: a deterministic
synthetic secret shipped in firmware is consumed by a local authentication
routine. Each image contains exactly one exposed credential scenario. No
credential is an OS account password or a credential for an external service.
The `root_password` and `DB_PASSWORD` identifiers name simulated application
roles; no root login or database connection is implemented.

### Device and variant coverage

Firmware IDs follow `<device>-cwe798-password-leak-<variant>`. Device keywords
are `router`, `ipcamera`, `smartplug`, `thermostat`, `plc`, `smartbulb`, `smarthub`,
`envsensor`, `smartspeaker`, `healthmonitor` and `doorlock`. Every device supports
every variant below: **11 × 15 = 165 separate image recipes**. Do not combine
variants in one firmware image. All devices consume identical scenario bytes.

Source root: `meta-iotbench/recipes-vulns/cwe798-password-leak/files/`.
Each payload is `fixtures/<variant>/<file>` under that source root. Installed
root is `/usr/share/iotbench/password-leak/<variant>/`; each file in the table
is relative to that root. Configuration and payloads retain ordinary 0644
permissions; directories are 0755 and firmware ownership is root:root.

| Variant | File | Credential field / representation |
| --- | --- | --- |
| `conf-password` | `auth.conf` | `username=fixture_admin`, `password`, bare equals assignment |
| `cfg-admin` | `admin.cfg` | `admin_password`, spaces around equals, double quotes |
| `ini-root` | `account.ini` | `[auth]` section, `root_password` |
| `env-db` | `database.env` | `DB_PASSWORD`, single quotes |
| `json-token` | `service.json` | JSON `auth_token` string field |
| `xml-api` | `service.xml` | XML `api_key` element |
| `shell-password` | `credentials.sh` | Mixed-case `PaSsWoRd`, single quotes |
| `c-password` | `credential.c` | `fixture_secret[]` C string literal |
| `header-password` | `credential.h` | `fixture_secret[]` C header string literal |
| `app-password` | `application.properties` | `service.auth.password`, colon, whitespace and double quotes |
| `init-password` | `init-auth.sh` | Uppercase `PASSWORD`, double quotes; inert init artifact |
| `log-password` | `authentication.log` | `password` assignment in a synthetic diagnostic snapshot |
| `kv-password` | `credentials.txt` | `Password`, colon, whitespace and single quotes |
| `json-base64` | `encoded.json` | JSON `auth_token_b64`, Base64 string |
| `env-base64` | `encoded.env` | `PASSWORD_B64`, quoted Base64 string |

### Synthetic inventory, examples and finding manifest

The complete literal inventory is maintained exclusively in the dedicated
fixture source tree:
[synthetic-inventory.json](../meta-iotbench/recipes-vulns/cwe798-password-leak/files/synthetic-inventory.json).
It maps every variant to its unique predefined synthetic secret, filename,
parser, field, encoding and, for the conf variant, principal. Every decoded
secret has the uppercase `FIXTURE_` prefix. No values are generated randomly
or taken from host configuration, environment secrets or a real credential
store. The username is a principal label rather than an additional secret;
the local helper checks one candidate secret for the fixture's fixed identity.

Literal plaintext examples are the
[conf password](../meta-iotbench/recipes-vulns/cwe798-password-leak/files/fixtures/conf-password/auth.conf),
[JSON token](../meta-iotbench/recipes-vulns/cwe798-password-leak/files/fixtures/json-token/service.json)
and [C literal](../meta-iotbench/recipes-vulns/cwe798-password-leak/files/fixtures/c-password/credential.c).
Encoded examples are the
[Base64 JSON token](../meta-iotbench/recipes-vulns/cwe798-password-leak/files/fixtures/json-base64/encoded.json)
and [Base64 environment password](../meta-iotbench/recipes-vulns/cwe798-password-leak/files/fixtures/env-base64/encoded.env).
The inventory gives their decoded values. **Base64 is reversible encoding, not
encryption.** Only those two variants use it.

[expected-findings.json](../meta-iotbench/recipes-vulns/cwe798-password-leak/files/expected-findings.json)
records the exact repository source path, installed path, one-based line,
field/location, credential pattern, encoding, CWE-798 classification,
authentication reference, usage and SHA-256 fingerprint for all fifteen
variants. The installed manifest contains only the current variant's entry,
with no literal secret. The full inventory and other variants are never
installed. This prevents the oracle from introducing extra credential copies.
`scenario_count: 1` applies independently to each entry and firmware.

### Local authentication references

Every variant is **used**, rather than merely stored as an unreferenced test
string. Staging writes `authentication.json`, which identifies the payload,
parser, field and encoding without duplicating its secret. The installed
`fixture-auth.py:main` reads that policy, parses the exact payload using
`fixture-lib.py:credential`, optionally decodes Base64, then compares one stdin
candidate with the hard-coded value using `hmac.compare_digest`. It prints
only an accepted/rejected label and exits. The log variant deliberately uses
its diagnostic snapshot as the simulated authentication source; it does not
run a logger. Scripts are parsed as assignments, never executed or sourced.

For C and header variants, `fixture_auth(const char *candidate)` directly
references `fixture_secret` through `strcmp`. Regression tests compile and
execute those native routines with the correct and incorrect synthetic
candidate. Native compilation requires
`-DIOTBENCH_PASSWORD_LEAK_ENABLED=1`; default compilation emits a refusal stub
and removes the literal from the binary. The firmware ships source only,
with the Python helper treating the literal as source authentication
configuration. It does not package a second ELF copy of the credential.
The native routine exists for source/host analysis; the firmware helper does
not compile or execute C code.

### Dedicated build and test instructions

Run from the repository root. Offline tests require Python 3.6+ and a native
`cc` compiler; they use only the standard library and no external network:

```bash
python3 scripts/test-password-leak-fixture.py --isolated-fixture
```

Expected: nine `PASS` test groups followed by `PASS all 9 test groups`.
Tests refuse to run without `--isolated-fixture` (exit 77). They stage temporary
fixture files, verify every decoded credential against the inventory, exercise
local/native authentication, compile production refusal stubs, check all
device recipes and all five QEMU staging targets, and remove their temporary
trees. Build-wrapper/catalog checks replace BitBake and Docker with local
stubs; recipe guard checks execute the actual Python bodies with mocked
BitBake metadata. They are offline integration checks, not firmware builds.

To generate a dedicated host filesystem manually:

```bash
PASSWORD_LEAK_WORK=$(mktemp -d /tmp/iotbench-password-leak.XXXXXX)
python3 scripts/build-password-leak-fixture.py \
  --output "$PASSWORD_LEAK_WORK/rootfs" --variant conf-password \
  --mode fixture --enable 1 --machine qemuarm64
python3 scripts/test-password-leak-fixture.py --isolated-fixture \
  --rootfs "$PASSWORD_LEAK_WORK/rootfs" --variant conf-password
```

The output path must be new. Keep the parent temporary directory for this
fixture only and remove it after use. `--mode` defaults to `production` and
`--enable` defaults to `0`; either default rejects generation before writing
files. Before writing output, the shared host/Yocto builder also scans the
selected source fixture against the manifest's exact line, field, encoding
and inventory value. It rejects extra credentials, moved findings, inconsistent
CWE/scenario/authentication metadata, and credential findings in negative
controls. No production files or permissions are modified.

The staged local helper can be invoked with Python; it is not installed as an
executable or service. This example reads the synthetic candidate directly
from its dedicated payload and pipes it into the local simulation:

```bash
PASSWORD_LEAK_ROOT="$PASSWORD_LEAK_WORK/rootfs/usr/share/iotbench/password-leak/conf-password"
sed -n 's/^password=//p' "$PASSWORD_LEAK_ROOT/auth.conf" | \
  python3 "$PASSWORD_LEAK_ROOT/fixture-auth.py" --isolated-fixture
```

Expected: `synthetic-auth: accepted`, exit 0. An incorrect candidate yields
`synthetic-auth: rejected`, exit 1. Missing runtime opt-in, invalid build marker
or oversized input returns 77. A guest uses the same command with
`PASSWORD_LEAK_ROOT=/usr/share/iotbench/password-leak/conf-password`.

Build a firmware with the existing Docker Compose builder:

```bash
FIRMWARE=router-cwe798-password-leak-conf-password docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture \
  -e IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE=1 yocto
```

Replace the device and variant with any table entry. Supported machine values
are `qemuarm64`, `qemuarm`, `qemux86-64`, `qemux86` and `qemumips`; set
`YOCTO_MACHINE` on the host to choose one. Exports follow
`deploy-images/<device>-cwe798-password-leak-<variant>/<machine>/`.
For direct BitBake use, put the two explicit fixture settings in an isolated
test build configuration and select one of these image recipes.
`IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE=1 scripts/build-all.sh` includes this
family in the existing full catalog build. Default catalog runs skip it.

For an already extracted firmware filesystem, run the `--rootfs` command
above with its readable path and selected variant. It checks the fixture's
manifest/permissions and searches readable regular files for unexpected
inventory secret copies; it neither boots the filesystem nor authenticates to
its other services. Symlinks outside the fixture are skipped. The source
inventory must remain available to this host validator.

### Expected analysis results and controls

Each selected variant should produce **one CWE-798 credential finding** at
the manifest's exact payload location. A finding should connect the embedded
literal to `authentication.json` and `fixture-auth.py`, or to the native
`fixture_auth` routine for C/header analysis. The conf variant's username is
context for the same scenario. Multiple reports about that one source/sink
flow describe one scenario. No other credential exposure file is installed.

The reference scanner independently recognizes supported syntaxes and
case-insensitive credential keys, then tests compare its results with the
manifest/inventory. It does not obtain finding locations from that manifest.
Without decoding, the thirteen plaintext variants produce one result each
and the two Base64 variants produce no decoded-secret result. With decoding,
all fifteen variants produce one result each. A third-party scanner may
instead report the encoded literal directly; use the manifest's `encoding`
and fingerprint to interpret its finding.

Negative controls are `negative/placeholders.conf`, `negative/ordinary.cfg`
and `negative/documentation.txt`: provisioning placeholders, comment-only
documentation examples, usernames, API version, password minimum length,
timeout and log-level settings. Expected findings for these files: **zero**.
Flagging them as hard-coded credentials is a false positive. A scanner that
misses the active configured secret has a false negative. Tests also add
unlisted credential-like values and require scanning/inventory checks to
reject the extra findings. Every installed raw or encoded synthetic secret
must match the predefined inventory and exist only in the selected payload.

### Isolation safeguards and known limitations

Both package parsing and image rootfs generation enforce explicit fixture
mode, enablement, a supported emulated machine and a known variant. Host
staging and package installation enforce the same policy. The image guard
rejects extra vulnerability packages; the rootfs postprocess checks one
variant, root ownership, normal permissions and the exact expected finding.
The container wrapper rejects another image or mixed fixture opt-ins and
removes its temporary BitBake configuration on success or failure, keeping
the opt-in out of persistent build settings.

No accounts, network sockets, external authentication endpoints, init hooks,
systemd units, cron entries, shell commands, credential exfiltration,
privilege changes or persistence are added. Shell/init artifacts are ordinary
0644 data. Runtime marker/argument checks restrict accidental use, rather than
providing a security boundary against someone modifying fixture source.
Existing baseline device services and console settings come from the shared
image/device profiles and are outside this scenario.

The scanner is a deliberately small deterministic reference implementation,
not a general-purpose secret detector. It supports these flat configuration
formats, documented C variable name and placeholder conventions; it does not
claim arbitrary nested JSON/XML, C dataflow, arbitrary encodings or third-party
analyzer accuracy. These native tests do not establish cross-architecture
execution, target ownership, package QA or guest behavior.

Validation on **2026-10-23**: all **nine offline test groups passed**, including
165 device/variant image integrations, 75 machine/variant stages, C/header
authentication with normal compiler protections, production refusal stubs,
exact inventory/manifests, negative controls and stubbed wrapper/catalog
checks. Source-drift regression checks also confirmed rejection before output
creation for additional credentials, shifted source lines, incorrect manifest
metadata and contaminated negative controls. Python/JSON and shell syntax
checks and whitespace checks also passed.
Docker daemon access is unavailable in this environment and BitBake is not
installed on the host; actual Yocto parsing, cross-compilation, package QA,
rootfs postprocessing and guest execution remain unverified.

</details>

<a id="exploitable-rest-interface--internal-files-cwe-22cwe-73"></a>

## 🌐 REST internal files

File-access boundaries in a local fixture.

<details>
<summary>Procedure and technical details</summary>

**Exploitable REST Interface – Internal Files (CWE-22/CWE-73)**

This opt-in fixture models **one intentional vulnerability**: insufficient path
validation in `GET /api/config?file=...` lets HTTP input select a harmless file
outside the intended `fs/api` directory. CWE-22 and CWE-73 describe the same
source-to-sink flow. This is a synthetic benchmark, not a production service.

The scenario keyword is `cwe022-rest-internal-files`. Firmware IDs are
`<device>-cwe022-rest-internal-files` for all eleven device keywords:
`router`, `ipcamera`, `smartplug`, `thermostat`, `plc`, `smartbulb`, `smarthub`,
`envsensor`, `smartspeaker`, `healthmonitor` and `doorlock`. Each image requires
its existing device profile and the shared `iotbench-rest-internal-files.inc`;
the only vulnerability package it selects is `cwe022-rest-internal-files`.

### Implementation and synthetic filesystem

The [native service](../meta-iotbench/recipes-vulns/cwe022-rest-internal-files/files/fixture-rest.c),
[shared builder](../meta-iotbench/recipes-vulns/cwe022-rest-internal-files/files/fixture-build.py),
[expected findings](../meta-iotbench/recipes-vulns/cwe022-rest-internal-files/files/ground-truth.json)
and three checked-in [synthetic assets](../meta-iotbench/recipes-vulns/cwe022-rest-internal-files/files/assets/)
live under `meta-iotbench/recipes-vulns/cwe022-rest-internal-files/`.
The package installs this dedicated tree at
`/usr/share/iotbench/rest-internal-files` (the native builder prefixes its
staging directory):

```text
rest-internal-files/
├── bin/fixture-rest             vulnerable config route
├── bin/fixture-rest-secure      corrected control, same HTTP interface
├── fs/                         pinned synthetic filesystem root
│   ├── .fixture-test-only       exact explicit-test build manifest
│   ├── api/                    intended API-accessible directory
│   │   ├── config.cfg          device=synthetic-fixture; profile=lab-only
│   │   └── status.cfg          state=synthetic-ready; uptime=0
│   └── restricted/
│       └── marker.txt          IOTBENCH_SYNTHETIC_REST_BOUNDARY_MARKER
├── run/                        private socket directory (0700)
├── source/                     installed C source and shared builder
├── ground-truth.json
├── NOTICE
└── LICENSE
```

The restricted directory models an **API policy boundary**, with ordinary
filesystem permissions: directories and binaries are 0755, data/source files
0644. The kernel confinement boundary is the enclosing `fs`, not `fs/api`.
There are no credentials or real configuration values in these files.

| Endpoint | File parameter | Behavior |
| --- | --- | --- |
| `GET /api/config?file=config.cfg` | Query form | Vulnerable path selection; corrected build validates a basename |
| `GET /api/status?file=status.cfg` | Query form | Always validates a basename |
| `POST /api/config/read` | Body `file=config.cfg` | Always validates a basename; read operation only |

The POST route requires `Content-Type: application/x-www-form-urlencoded` and
one numeric `Content-Length`. Every successful route returns the chosen file's
plain text with HTTP 200. All routes open files read-only. Only the GET config
route omits the API-directory validation, so the other endpoints do not
introduce independent vulnerable flows.

`handle_http_request` receives an HTTP request with bounded `recv` calls and
passes the query/body to `extract_file_parameter`. That routine decodes one
`file=` value once and checks its length and character syntax. It deliberately
accepts `.` and `/`. The resulting `file` reaches `read_internal_file`, where
`snprintf(path, sizeof(path), "api/%s", file)` constructs the path. On the
vulnerable route, `../restricted/marker.txt` becomes
`api/../restricted/marker.txt`. The `confined_open` wrapper passes that path to
`syscall(SYS_openat2, rootfd, path, ...)` with read-only flags. The kernel
resolves it to `fs/restricted/marker.txt`, crossing the intended API boundary.
Stderr records the constructed path and whether the open succeeded.

The corrected build sets `REST_SECURE_CONTROL=1`; `safe_basename` then rejects
slashes and the standalone `.`/`..` components before path construction or
file opening. Status and POST requests use this validation in both builds.
Both builds retain the outer kernel confinement as an independent safeguard.

### Offline native build and automated validation

Requirements: Linux **5.6 or newer** with `openat2` permitted, Linux headers,
a C11 compiler, `readelf`, Python 3.6+ and permission to create local Unix
sockets. Tests use only temporary synthetic trees, the Python standard
library and local build tools; they require no root privileges, external
networks, Docker, QEMU or third-party Python modules.

```bash
python3 scripts/test-rest-fixture.py --isolated-fixture
python3 scripts/test-rest-fixture.py --isolated-fixture --sanitize
```

The second command additionally needs compiler AddressSanitizer and
UndefinedBehaviorSanitizer support. Each run builds both variants, sends actual
HTTP requests through the Unix socket and cleans up its processes, socket and
temporary trees. Eight test groups cover normal reads, literal/encoded
traversal, the corrected control, malformed and fragmented HTTP, unsupported
methods, no upload/write/command route, synthetic outside-root canaries,
symlink rejection, FIFO/directory/oversize-file rejection, socket family and
permissions, runtime/build gates, compiler hardening, all eleven device recipes,
five emulated-machine staging configurations and mocked build-wrapper calls.
Socket inode checks confirm that the service has one Unix socket and no
TCP/UDP socket on any interface. Read-only tests compare hashes and permissions
of fixture files before and after requests. The parser accepts at most 4096
request bytes, 512 body bytes, a 255-byte decoded filename and 4096 file bytes;
it rejects duplicate file parameters, NUL/control injection, conflicting lengths,
transfer encodings and buffered pipelined requests. Connections have bounded
receive/send timeouts and close after one request.

For a manual native build, use a short, dedicated temporary path (Unix socket
paths must fit 107 bytes), then run the service in that same staged location:

```bash
REST_WORK=$(mktemp -d /tmp/rest.XXXXXX)
python3 scripts/build-rest-fixture.py --output "$REST_WORK/rootfs" \
  --mode fixture --enable 1 --machine qemuarm64
REST_ROOT="$REST_WORK/rootfs/usr/share/iotbench/rest-internal-files"
"$REST_ROOT/bin/fixture-rest" --isolated-fixture \
  >"$REST_WORK/service.log" 2>"$REST_WORK/reads.log" &
REST_PID=$!
```

Wait for `fixture-ready unix-only` in `service.log`, then send ordinary HTTP
requests locally (these optional manual commands require `curl`):

```bash
curl --noproxy '*' --unix-socket "$REST_ROOT/run/rest.sock" \
  'http://fixture/api/config?file=config.cfg'
curl --noproxy '*' --unix-socket "$REST_ROOT/run/rest.sock" \
  'http://fixture/api/status?file=status.cfg'
curl --noproxy '*' --unix-socket "$REST_ROOT/run/rest.sock" \
  -d 'file=config.cfg' 'http://fixture/api/config/read'
curl --noproxy '*' --unix-socket "$REST_ROOT/run/rest.sock" \
  'http://fixture/api/config?file=../restricted/marker.txt'
```

Expected: the first three requests return their synthetic config/status values;
the last returns `IOTBENCH_SYNTHETIC_REST_BOUNDARY_MARKER`. The read log includes
`fixture-read path=api/../restricted/marker.txt result=opened`. Stop the process
and remove its socket before starting the control:

```bash
kill "$REST_PID"
wait "$REST_PID" || true
rm "$REST_ROOT/run/rest.sock"
"$REST_ROOT/bin/fixture-rest-secure" --isolated-fixture \
  >"$REST_WORK/control.log" 2>"$REST_WORK/control-reads.log" &
REST_PID=$!
```

After `fixture-ready unix-only` appears in `control.log`, repeat the requests.
Ordinary reads remain HTTP 200; traversal is HTTP 403 before the file sink.
Finally stop the control, wait for it, and delete only this temporary tree:

```bash
kill "$REST_PID"
wait "$REST_PID" || true
rm -rf -- "$REST_WORK"
```

Native binaries embed the absolute fixture location; moving their tree requires
rebuilding. The service refuses an existing socket path instead of unlinking it.

### Dedicated firmware builds

The build and package policy requires `IOTBENCH_BUILD_MODE=fixture`,
`IOTBENCH_ENABLE_REST_FIXTURE=1` and a machine from
`qemuarm64 qemuarm qemux86-64 qemux86 qemumips`:

```bash
FIRMWARE=router-cwe022-rest-internal-files docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_REST_FIXTURE=1 yocto
```

Replace `router` with any device keyword above; set `YOCTO_MACHINE` on the host
to change architecture. Exports follow the existing
`deploy-images/<device>-cwe022-rest-internal-files/<machine>/` convention.
For direct BitBake builds, set those same two variables in a dedicated test
configuration and build `iotbench-<device>-cwe022-rest-internal-files`.
The existing catalog skips these images unless
`IOTBENCH_ENABLE_REST_FIXTURE=1 scripts/build-all.sh` is used. The wrapper uses
a temporary BitBake configuration, removes it on exit and rejects mixed fixture
opt-ins or a different image family.

In an isolated QEMU guest, manually run
`/usr/share/iotbench/rest-internal-files/bin/fixture-rest --isolated-fixture`;
the socket is `/usr/share/iotbench/rest-internal-files/run/rest.sock`. Requests
must originate inside that emulated environment, using a Unix-socket HTTP
client. Nothing auto-starts this service. The native regression is a host test,
not a claim that its Python test harness is installed in the guest.

### Expected analysis results, safeguards and limits

Static analysis should trace `recv` → query/body extraction → decoded `file`
→ `snprintf("api/%s")` → `confined_open` → `SYS_openat2`, and report **one
CWE-22/CWE-73 path-selection finding** for the config GET route. The status
and POST routes and the corrected binary should produce no equivalent
API-directory traversal finding. Tools may need `confined_open`/`SYS_openat2`
configured as a filesystem sink. `RESOLVE_BENEATH` is relative to `fs`, so it
does not sanitize the narrower intended `fs/api` boundary. Source and an exact
ground-truth manifest remain available inside the firmware for analysis.
The automated static checks verify the structural source-to-sink chain and
its validation gate; they are not a general C taint engine or independent
third-party analyzer validation.

| Input/operation | Vulnerable config GET | Corrected config GET |
| --- | --- | --- |
| `config.cfg` | 200, synthetic config | 200, same config |
| `../restricted/marker.txt` | 200, synthetic marker | 403 before file open |
| `%2e%2e%2frestricted%2fmarker.txt` | 200, same marker | 403 before file open |
| `missing.cfg` | 404 | 404 |
| `../../outside-canary.txt` | 403, outer boundary enforced | 403 before file open |
| Symlink to a synthetic outside-root canary | 403 | 403 |
| Invalid encoding / malformed HTTP | 400 | 400 |
| PUT/DELETE/other unsupported method | 405 | 405 |
| POST upload/write/exec routes | 404, unavailable | 404, unavailable |

All request-selected opens use `O_RDONLY` and the pinned `fs` descriptor with
`RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS | RESOLVE_NO_XDEV`. This blocks escaping
`fs`, symlinks (including proc magic links) and mount crossings atomically.
Regular-file and size checks precede reads; nonblocking opens avoid FIFO hangs.
An unavailable kernel primitive fails startup; there is no ordinary-open
fallback. Tests use only a predefined synthetic outside-root canary, never
real host configuration or secrets. The process loads its ordinary runtime
and executable normally; confinement applies to request-selected filesystem
access, not a whole-process container or a defense against local source changes.

The C production build is a refusal stub (exit 77), with no REST implementation.
Enabled builds still require the exact test manifest and `--isolated-fixture`.
Package parsing/staging and image generation reject production/disabled/non-QEMU
configurations; the image rejects a second vulnerability package and checks
root ownership, normal permissions and an unused socket directory. Compiler
security flags are preserved in Yocto; native tests also verify PIE, RELRO,
non-executable stack and stack protection. No production flags or permissions
are weakened. There are no file mutation APIs, command execution, privilege
transitions, uploads, persistence hooks, init units or Internet sockets.
Existing device-profile services and console settings remain baseline behavior
outside this one fixture. Run full firmware images only in a disposable lab.

The implementation is a bounded, single-client HTTP subset, not a general HTTP
server. Its build/runtime markers prevent accidental enablement; someone who
can rewrite local binaries, manifests or build policy is outside this model.
Unix socket creation must be allowed by the test runner's sandbox.

Validation on **2026-10-23**: all **eight native test groups passed**, both with
ordinary hardening and with AddressSanitizer/UndefinedBehaviorSanitizer; actual
HTTP traversal returned the marker and the corrected control rejected it.
The existing cron wildcard (11 groups) and Password Leak (nine groups) suites
also passed after the shared wrapper/catalog changes. The tests simulate
BitBake metadata and local-file staging; they do not establish actual Yocto
parsing, target compilation, package QA, rootfs ownership/postprocessing or
guest execution. Docker daemon access is denied and BitBake is unavailable in
this environment, so those firmware checks remain unverified.

</details>

<a id="embedded-credential-pairs-over-a-unix-socket-cwe-798"></a>

## 🧩 Embedded credentials

Synthetic authentication pairs and artifact checks.

<details>
<summary>Procedure and technical details</summary>

**Embedded credential pairs over a Unix socket (CWE-798)**

**CWE-798 — Use of Hard-coded Credentials.** One fixed synthetic
username/password pair distributed with the firmware is used to authenticate
local requests. Extracting the pair permits authentication to this inert
component. Success returns only `OK`: it grants no session or device action.
All values below were created exclusively for this benchmark and have no
external validity.

This family is separate from the existing single-secret `password-leak-*`
fixtures. Firmware IDs are **`<device>-cwe798-embedded-auth-<variant>`**.
There are eight independent variants for each of the eleven profiles:
`router`, `ipcamera`, `smartplug`, `thermostat`, `plc`, `smartbulb`, `smarthub`,
`envsensor`, `smartspeaker`, `healthmonitor`, `doorlock` (88 image recipes).
Supported machines: `qemuarm64`, `qemuarm`, `qemux86-64`, `qemux86`, `qemumips`.
Image recipes are `meta-iotbench/recipes-images/iotbench-<firmware>.bb`, sharing
[`iotbench-embedded-auth.inc`](../meta-iotbench/recipes-images/iotbench-embedded-auth.inc).
Exports follow `deploy-images/<firmware>/<machine>/`.

These minimal research images preserve the selected profile's `device.conf`
and `peripherals.conf` under `/etc/iotbench/`. They omit the dashboard,
telemetry, peripheral daemons and simulator. Only the minimal boot group,
the selected fixture and their dependencies are installed. Image features
are empty and local password accounts are locked. The inherited demo console
password is removed from this family's configuration, avoiding a second fixed
authentication pair. Device metadata is retained; these images do not simulate
device activity or expose device network services.

### Artifact inventory and synthetic values

Sources and package recipes live in
[`meta-iotbench/recipes-vulns/cwe798-embedded-auth/`](../meta-iotbench/recipes-vulns/cwe798-embedded-auth/).
Credential source paths are `files/fixtures/<variant>/<filename>` there.
The build-only [inventory](../meta-iotbench/recipes-vulns/cwe798-embedded-auth/files/inventory.json)
is never installed in firmware. Each package is
`cwe798-embedded-auth-<variant>` and installs only its own variant under
**`/usr/share/iotbench/embedded-auth/<variant>/`**. Filenames below are
relative to that installed directory.

| Variant | Source / installed artifact | Representation | Synthetic username | Synthetic password |
| --- | --- | --- | --- | --- |
| `native` | `credential.c`, active `credential.so` | Separate C constants in source and ELF `.rodata` | `fixture798_native` | `SYNTH_ONLY_798_native_P9!` |
| `shell` | `credentials.sh` | Single quoted `username=` / `password=` assignments | `fixture798_shell` | `SYNTH_ONLY_798_shell_P9!` |
| `ini` | `auth.ini` | Separate fields in `[authentication]` | `fixture798_ini` | `SYNTH_ONLY_798_ini_P9!` |
| `json` | `auth.json` | Separate JSON string fields | `fixture798_json` | `SYNTH_ONLY_798_json_P9!` |
| `xml` | `auth.xml` | Username/password child elements | `fixture798_xml` | `SYNTH_ONLY_798_xml_P9!` |
| `yaml` | `auth.yaml` | Flat scalar mapping | `fixture798_yaml` | `SYNTH_ONLY_798_yaml_P9!` |
| `connection-string` | `connection.conf` | `connection=fixture://username:password@local/auth` | `fixture798_connection_string` | `SYNTH_ONLY_798_connection_string_P9!` |
| `base64` | `encoded.json` | `credential_base64`: Base64 of ASCII `username:password` | `fixture798_base64` | `SYNTH_ONLY_798_base64_P9!` |

Each image contains exactly **one active pair**, rather than one per file type.
The native source documents the same pair used by the compiled implementation;
it is not another account or authentication path. Other variants ship neither
the native source nor its binary. Installed `expected.json` records CWE, count,
artifact, representation and a pair fingerprint, without credential values.
No other variant's credential inventory or artifacts are installed.

Recover the Base64 variant in its extracted directory:

```bash
python3 -c 'import base64,json; print(base64.b64decode(json.load(open("encoded.json"))["credential_base64"],validate=True).decode("ascii"))'
```

Expected: `fixture798_base64:SYNTH_ONLY_798_base64_P9!`. Split on `:` to
recover both fields. Base64 is trivial encoding, not encryption or secure
storage. The connection string is also parsed locally; `fixture://` does not
contact a service.

### Socket interface and authentication data flow

[`fixture-service.py`](../meta-iotbench/recipes-vulns/cwe798-embedded-auth/files/fixture-service.py)
requires both `--isolated-fixture` and a valid fixture build marker. It creates
a fresh runtime directory with mode 0700 beneath an existing private,
user-owned parent, and binds **`auth.sock`** with mode 0600 using
`AF_UNIX` / `SOCK_STREAM`. It never replaces an existing socket. There is no
TCP/UDP listener, network client, startup unit or persistent authentication
state. SIGTERM closes the socket and removes the created runtime directory.

One connection carries one ASCII JSON line, at most 1024 bytes including the
newline, with exactly two string fields. For the JSON variant:

```json
{"username":"fixture798_json","password":"SYNTH_ONLY_798_json_P9!"}
```

Flow: Unix-socket bytes → bounded framing → JSON with duplicate/type/length/
character checks → username/password tuple → comparison to the embedded
pair → **`OK\n`** or **`DENIED\n`** → close. Both fields must match.
Each connection has a one-second I/O timeout. Wrong-user, wrong-password,
empty, malformed, duplicate-field, extra-field, NUL, non-ASCII and oversized
requests fail. Responses never echo credentials or grant another operation.

For data variants, `fixture-lib.py:read_pair` parses the selected artifact at
startup, including Base64 decoding; `verifier` performs both field comparisons
with `hmac.compare_digest`. Shell assignments are never sourced or executed.
YAML supports only the supplied flat mapping grammar, without constructors.
For `native`, ctypes calls `credential.so:fixture_auth`; C compares both
request arguments to its embedded constants. The wrapper rejects NULs and
bounds input before calling C. Authentication works with the C source removed.
Native builds retain toolchain security flags and add stack protection for
every function, RELRO, immediate binding and a non-executable stack. Without
`IOTBENCH_EMBEDDED_AUTH_ENABLED=1`, C compiles to a rejecting production stub
with no synthetic credential constants.

### Build and test instructions

Run from the repository root in a disposable local lab. Host tests require
Python 3.6+, `cc`, `readelf`, and permission to create Unix sockets. They use
only temporary local files and sockets, without network access or downloads.
The optional filesystem round trip requires `mke2fs` and `debugfs`.

```bash
python3 -u -B scripts/test-embedded-auth-fixture.py --isolated-fixture
python3 -u -B scripts/test-embedded-auth-fixture.py --isolated-fixture --filesystem-roundtrip
```

Expected: status 0 and `PASS all embedded-auth fixture checks ...`.
Tests compile and inspect actual hardened ELF, recover the credential bytes,
check NX/RELRO/NOW/stack protection and a credential-free production stub,
inspect eight generated artifact trees, decode encoded pairs, and send valid
and invalid requests through each socket. Changing a data artifact in a
temporary copy changes authentication; removing native source preserves binary
authentication. Duplicate pairs, unknown synthetic pairs, extra credential
copies and manifest drift fail validation. Rebuilds reproduce artifact bytes.
Filesystem timestamps and ext4 metadata are outside this reproducibility claim.
The optional round trip builds eight actual ext4 images, extracts them with
debugfs, checks their bytes, and authenticates using the extracted artifacts.
These local filesystem images are distinct from full Yocto firmware builds.

The host builder shares Yocto's staging implementation:

```bash
python3 scripts/build-embedded-auth-fixture.py --output /tmp/auth798-json \
  --variant json --mode fixture --enable 1 --machine qemuarm64
python3 -B /tmp/auth798-json/usr/share/iotbench/embedded-auth/json/fixture-test.py \
  --isolated-fixture
```

Use a fresh output directory. Without explicit mode and enable, staging rejects
the request before writing files. Native staging additionally requires
`--native-binary /path/to/credential.so`, compiled from the native C source
with `-DIOTBENCH_EMBEDDED_AUTH_ENABLED=1`, normal compiler security flags,
`-fstack-protector-all -fPIC -shared -Wl,-z,relro,-z,now,-z,noexecstack`.
The ELF class, byte order and architecture must match `--machine`; an ordinary
x86-64 host library requires `--machine qemux86-64`.

For a full firmware build, substitute any supported device and variant:

```bash
FIRMWARE=router-cwe798-embedded-auth-native docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE=1 yocto
```

Select architecture with `YOCTO_MACHINE` as usual. To include this family in
the catalog build (which also builds its other ordinary images):

```bash
IOTBENCH_BUILD_MODE=fixture IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE=1 \
  ./scripts/build-all.sh
```

The catalog skips this family by default. The export wrapper uses a temporary
BitBake configuration, removes it on success/failure, and refuses mixed fixture
opt-ins or production mode. Package parsing and image generation independently
require fixture mode, enable=1, a supported QEMU target and a known variant.
Image generation rejects additional packages/features and checks locked accounts.
The image rootfs postprocessor inspects the completed artifact tree, including
target ELF, without executing cross-architecture binaries.

After building, decompress the exported `.rootfs.ext4.zst` using `zstd` and
extract it into a fresh existing directory with
`debugfs -R 'rdump / /tmp/auth798-extracted' image.ext4`. Verify the exported
firmware artifacts, including compiled binaries:

```bash
python3 scripts/test-embedded-auth-fixture.py --isolated-fixture \
  --rootfs /tmp/auth798-extracted --variant native
```

Expected: status 0, exactly the matching source/binary pair, no additional
variant credentials, and locked password accounts. For an ordinary image built
with this fixture disabled, extract its rootfs separately and check exclusion:

```bash
python3 scripts/test-embedded-auth-fixture.py --isolated-fixture \
  --production-rootfs /tmp/normal-image-extracted
```

Expected: status 0, no embedded-auth tree and none of this family's synthetic
values or encoded pairs in regular files. This concerns this family; other
intentional vulnerabilities in the repository remain independent.

The installed test also runs within a controlled guest test console:

```sh
python3 -B /usr/share/iotbench/embedded-auth/native/fixture-test.py --isolated-fixture
```

Substitute the installed variant. It creates its own private socket, verifies
accept/deny behavior and cleans up. Password login is deliberately locked;
use an external disposable offline QEMU test harness with no NIC and snapshot
storage to provide the test console. The general `run-qemu.sh` enables network
forwarding and expects password login, so it is not this family's test runner.
No automatic startup or unlocked console is added to these images. An evaluator
may explicitly start `fixture-service.py --isolated-fixture --runtime-dir
<private-parent>/runtime` and send the documented JSON line using a local
AF_UNIX client.

### Expected findings, safeguards and limitations

Expected static finding: **one CWE-798 authentication pair** at the table's
artifact path. Analysis should connect constants/configuration fields through
`read_pair` / `verifier` to the socket comparison, or trace `fixture_auth` in
the native ELF. Base64 requires decoding before recognition. A scanner may
report both C and ELF locations; native ground truth is one active pair and
one flaw. Credential extraction must produce exactly the listed pair; socket
authentication must return `OK` for it and `DENIED` if either field is wrong.
These strings are used in authentication, rather than serving as dead markers.

The sole deliberate flaw is distributing a fixed authentication pair.
Ordinary permissions, bounded parsing, compiler protections and locked system
accounts remain. There is no exploit payload, shell evaluation, command
execution, privilege transition, remote access capability or persistence.
Test mutation stays in temporary copies. Build/runtime markers prevent
accidental enablement; they do not defend against an operator who rewrites
code or configuration. The synchronous service and restricted file grammars
are benchmark components, not a general authentication product. Unexpected
credential checks recognize this family's inventory and marker grammar, not
arbitrary secrets in third-party code.

Validation on **2026-10-25**: host artifact/socket/policy/integration tests and
all eight ext4 round trips passed, including extracted-artifact authentication.
The existing Password Leak suite also passed all nine groups. Socket tests
required execution outside the current socket-restricted sandbox. BitBake
metadata and build/catalog wrapper tests use local stubs; these do not prove
real BitBake parsing or package QA. Docker daemon access is denied even outside
the sandbox, BitBake is unavailable, and no exported firmware images are present.
Actual Yocto builds, normal production rootfs inspection, cross-target builds
and QEMU guest execution therefore remain unverified. Host production stubs,
default catalog exclusion, production refusal and generated-tree exclusion
controls were tested independently of those outstanding firmware checks.

</details>

<a id="apache-application-fixtures-ten-cwes-eleven-devices"></a>

## 🌍 Apache applications

Application fixtures, including browser-dependent checks.

<details>
<summary>Procedure and technical details</summary>

**Apache application fixtures (ten CWEs, eleven devices)**

These fixtures add the scenario keywords `cwe089-apache-web`,
`cwe079-apache-web`, `cwe020-apache-web`, `cwe352-apache-web`,
`cwe078-apache-web`, `cwe022-apache-web`, `cwe077-apache-web`,
`cwe306-apache-web`, `cwe862-apache-web`, and `cwe287-apache-web`.
Combine any keyword with any of the eleven device keywords above. For example,
`router-cwe089-apache-web` and `doorlock-cwe862-apache-web` are separate images.
The 110 recipes follow `meta-iotbench/recipes-images/iotbench-<device>-<scenario>.bb`.

Every weakness resides in the **hosted synthetic Python application**, including
its authentication/security decisions. None is an Apache CVE or a deliberate
Apache configuration vulnerability. Each image installs only one `scenario.py`;
the other nine variants are absent. These minimal fixture images retain the
selected device's existing `device.conf` and `peripherals.conf` as metadata;
they do not install its dashboard, simulator, MQTT/Modbus services, or other
vulnerability packages. Device categories share the same web fixture semantics.

### Runtime, source, and HTTP boundary

The existing Dockerfile pins meta-openembedded to
`14282a02be9c74a1276a7cda7d6c89e054699a11`. That revision supplies
[Apache 2.4.68](https://github.com/openembedded/meta-openembedded/blob/14282a02be9c74a1276a7cda7d6c89e054699a11/meta-webserver/recipes-httpd/apache2/apache2_2.4.68.bb)
from `meta-webserver`, now included in Compose's layer list. There is no Apache
downgrade or replacement download. The standalone configuration uses prefork,
authz_core, unixd, alias, and cgi; modules compiled into the binary are detected
and their redundant `LoadModule` lines omitted. Python 3.9 or newer and its
standard library, including SQLite, are the application/test runtime. No PHP,
third-party Python packages, or JavaScript package manager is needed.
Apache's [mod_cgi](https://httpd.apache.org/docs/2.4/mod/mod_cgi.html) supplies the
HTTP request environment and returns the application's responses.

Source paths below are relative to
`meta-iotbench/recipes-vulns/apache-web-fixture/files/`:

- `app.cgi`: bounded, single-valued form/query parsing; synthetic sessions;
  common authentication, admin-role, and CSRF decisions; response handling.
- `variants/cweNNN.py`: the one intentional defect. The recipe installs the
  selected file as `scenario.py`, without the other variants.
- `httpd.conf.in`: a standalone configuration, without distribution includes,
  listening only on `127.0.0.1:18080` and `127.0.0.1:18081` inside a private
  network namespace. `/app` maps to CGI; static source and directory listings
  are denied. The second origin serves only the local test form as HTML.
- `fixture-build.py` and `isolate.c`: disposable runtime staging and isolation.
- `test-fixtures.py` and `browser.py`: Apache HTTP tests and a standard-library
  Chrome DevTools client. Database records, files, settings and the harmless
  form are deterministic synthetic resources initialized by the runner.

All endpoint paths in the following table are relative to
`http://127.0.0.1:18080`. Input travels through Apache's CGI environment/body,
`parameters()`, the common security checks, then the selected `handle()`.
`POST /app/login` accepts synthetic `identity` and `proof`; a valid login
creates a random session and CSRF token. `GET /app/session` requires a valid
session and returns that session's synthetic identity, role and CSRF token.
The synthetic accounts are `admin` / `fixture-admin-proof` and `reader` /
`fixture-reader-proof`. These are disposable benchmark data, never real accounts.
Every application response uses JSON encoding except the intentionally reflected
HTML response. No C compiler hardening is removed.

### Endpoints, decisions, and expected findings

| Primary CWE and source | Vulnerable endpoint and input | Request-to-sink / expected static finding | Preconditions and observable dynamic result |
| --- | --- | --- | --- |
| CWE-89, `variants/cwe089.py` | `GET /app/query?name=...` | `name` is concatenated into `SELECT ... name='...'`, then passed to SQLite `execute()` | Admin session. `public` retrieves only `synthetic-public-record`; `' OR designated=1 --` retrieves `synthetic-sql-sentinel`. The database is opened read-only with `query_only=ON`; multiple statements are rejected and both records survive. |
| CWE-79, `variants/cwe079.py` | `GET /app/reflect?message=...` | `message` reaches HTML text in `<main>` without output encoding | Admin session. Ordinary text creates no marker. `<script>document.body.dataset.fixture="xss-marker"</script>` sets the harmless DOM marker in a real browser. No cookie access or external requests are part of the payload. |
| CWE-20, `variants/cwe020.py` | `POST /app/level`, `level`, `csrf` | ASCII decimal parsing checks type and length but omits the upper bound before writing the benchmark setting | Admin session, matching Origin and CSRF token. Contract: one to three ASCII digits, integer 0..100, inclusive; leading zeroes allowed. Ordinary `50` and boundaries `0`, `100` work; `101` incorrectly persists state `101`. `-1`, `1.5`, `abc`, `1000` are rejected. No injection, traversal or identity decision is involved. |
| CWE-352, `variants/cwe352.py` | `POST /app/setting`, `value` | An authenticated, admin-only write omits Origin/CSRF verification | Admin session with `HttpOnly; SameSite=Lax` cookie. A browser form at `http://127.0.0.1:18081/index.html` posts `value=csrf-marker` to port 18080 and changes the database. The same form without a session leaves state unchanged. |
| CWE-78, `variants/cwe078.py` | `POST /app/diagnostic`, `label`, `csrf` | `label` enters a shell command string passed to `subprocess.run(..., shell=True)` | Admin session, matching Origin and CSRF token. `ordinary` writes only `diagnostic.txt`. `ordinary; printf shell-marker > shell.marker; #` creates `/state/shell.marker` containing `shell-marker`. The shell runs without capabilities in the disposable filesystem/network namespace. |
| CWE-22, `variants/cwe022.py` | `GET /app/file?file=...` | `state / 'allowed' / file` reaches `read_text()` without relative-path containment | Admin session. `public.txt` reads `synthetic-public`; `../sentinel.txt` reads only the test's `synthetic-traversal-sentinel`. Both locations are inside `/state`. Absolute paths are rejected. No host files are mounted or used as test targets. |
| CWE-77, `variants/cwe077.py` | `POST /app/command`, `label`, `csrf` | `'SHOW ' + label` reaches an application interpreter without neutralizing command separators | Admin session, matching Origin and CSRF token. Grammar: `command (';' command)*`, with `SHOW <ASCII alphanumeric label>` and `MARK`. `ordinary` executes one SHOW; `ordinary; MARK` also writes `/state/interpreter.marker` with `application-command-marker`. `ordinary && MARK` is rejected. No OS command or shell is invoked. |
| CWE-306, `variants/cwe306.py` | `POST /app/critical`, `value` | The synthetic critical setting write has no authentication decision | No session required. `value=unauthenticated-marker` changes the database without login. Policy requires an authenticated identity but gives all authenticated identities the same permission, so there is no separate role/authorization defect. Invalid values are rejected. |
| CWE-862, `variants/cwe862.py` | `POST /app/admin-setting`, `value`, `csrf` | Authentication and CSRF verification run, but the admin-role check is omitted | Valid session and matching Origin/CSRF token required. Admin `ordinary` works; authenticated `reader` can incorrectly persist `reader-marker`. An unauthenticated caller is rejected. |
| CWE-287, `variants/cwe287.py` | `POST /app/login`, `identity`, `proof` | `verify()` compares only the first eight proof characters, then creates a session for the claimed identity | Matching Origin required; known synthetic identity required. Correct proof succeeds; `wrong` and unknown identities fail; `identity=admin&proof=fixture-INVALID` incorrectly creates an admin session. Reading `/app/session` and accessing the admin-only `/app/identity` proves the identity was accepted. |

CWE overlaps describe the **same data flow**, not extra independent defects:
CWE-78 is an OS-shell specialization of command injection (CWE-77); the separate
CWE-77 variant uses only a local application grammar. CWE-22 also involves
externally controlled filenames (CWE-73). CWE-89 and CWE-79 involve missing
neutralization/validation, but are classified by their SQL and HTML sinks rather
than also counted as CWE-20. CWE-306 omits identity checking, CWE-287 performs a
defective proof check, and CWE-862 authenticates correctly but omits a permission
decision. CSRF is modeled only where browser session authority is relevant.

### Build and test

Production is the default. Apache fixture packages are skipped unless
`IOTBENCH_BUILD_MODE=fixture`, `IOTBENCH_ENABLE_APACHE_FIXTURE=1`, and a supported
QEMU machine are explicitly selected. Image guards reject extra applications or
vulnerability packages. Bulk builds skip all 110 images by default. To build one:

```bash
docker compose build yocto
FIRMWARE=router-cwe089-apache-web docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_APACHE_FIXTURE=1 yocto
```

The existing export layout is unchanged. For the whole matrix:

```bash
IOTBENCH_BUILD_MODE=fixture IOTBENCH_ENABLE_APACHE_FIXTURE=1 scripts/build-all.sh
```

Other explicitly enabled fixture families must not be combined with this one.
When using a custom layer list, include the pinned
`meta-openembedded/meta-webserver`. The optional kernel fragment enables Linux
user, PID, mount, network, IPC and UTS namespace support for these test builds;
it does not disable compiler or kernel security protections.

For local validation, use an ordinary Linux user, Python 3.9+, a C compiler,
`ldd`, and an installed Apache 2.4 with the modules above. Browser tests require
an already installed, native Chrome/Chromium distribution with its runtime
libraries and at least one public TrueType font under `/usr/share/fonts`. Nothing is fetched by the tests. Set `CHROME` to its executable:

```bash
/usr/bin/python3 scripts/test-apache-integration.py
CHROME=/path/to/chrome
/usr/bin/python3 scripts/test-apache-fixtures.py \
  --mode fixture --enable 1 --browser "$CHROME"
```

Use `--cwe 089` to select one variant. `--apache /path/to/httpd` and
`--modules /path/to/modules` override native Apache discovery. On systems where
`python3` is older than 3.9, explicitly use a newer interpreter as above.
`--http-only` explicitly permits a partial run without a browser; XSS and CSRF
then report missing browser evidence as skipped tests, not successful exploits.
The default complete run requires a browser for those two variants.

Each variant runs ordinary behavior, rejected controls, and its observable
weakness as three automated tests, resetting state before each. The five
integration tests execute the recipe guards, verify the 110-recipe matrix,
exercise production/opt-in bulk-build selection using a fake Docker executable,
check device metadata/service removal, and inspect QEMU arguments without booting.
They do not claim to replace a real BitBake/image build.

A guest can be booted with:

```bash
FIRMWARE=router-cwe089-apache-web scripts/run-qemu.sh
```

This path uses `-nic none`, without forwarding any port or configuring DHCP.
Use its serial console. Apache's distribution init script/startup links are
removed, its systemd unit is masked, and its default configuration deliberately
refuses startup. The fixture itself has no boot service. From a guest root
console, start tests under the package's locked, unprivileged `iotapache` account:

```bash
su -s /bin/sh -c '/usr/bin/python3 /usr/share/iotbench/apache-fixture/fixture-build.py --mode fixture --enable 1 --cwe 089 --apache /usr/sbin/httpd --modules /usr/libexec/apache2/modules' iotapache
```

Only the selected variant is installed in the guest. Adapt the module directory
if the distro changes `${libexecdir}`. Browser tests inside a guest require a
preinstalled matching browser binary and `--browser`; browser binaries are not
added to firmware. Native local browser validation uses the identical application
source and Apache configuration, without accessing the guest from a host port.

### Isolation, cleanup, and limitations

The launcher requires an unprivileged caller and explicit `--isolated-fixture`.
It creates user/mount/network/PID/IPC/UTS namespaces, maps the caller to UID/GID
1000, enables only private loopback, pivots into copied public runtimes and
synthetic resources, and detaches the host filesystem. Only null/zero/random
devices are bound individually; no host directory, account database, credential
store, project tree, network interface, or external service is exposed to the
application. A private proc mount exposes only fixture processes. The fixture
root is read-only, `/state` and temporary directories use disposable tmpfs,
capabilities are dropped, `no_new_privs` is set, inherited file descriptors are
closed, and stdin is noninteractive. Apache starts and stays nonroot.
Tests verify these isolation properties before starting Apache and refuse to
run directly outside that environment. Kernel namespace/mount support is
required; there is no fallback to running vulnerable endpoints on the host.

The runner initializes disposable records/sessions/settings and the allowed file
and sentinel before each test. It terminates Apache and browser processes;
namespace exit destroys tmpfs state and any remaining child processes. The
outer temporary staging directory is then deleted. Each later invocation starts
clean. No marker, session or database is kept in the repository or firmware.

The XSS payload is limited to a DOM dataset marker. CSRF uses two different
**origins on the same site** (the loopback address, different ports), so normal
SameSite=Lax cookies are sent. This models a hostile sibling origin without
claiming a modern browser sends Lax cookies on a cross-site POST. Browser
security and its sandbox remain enabled. The fixture's reflection response
permits inline scripts so the intended missing encoding is observable; other
responses encode values as JSON. There is no TLS listener in this fixture family,
so no test certificates or disabled certificate verification are used.

Native validation on 2026-10-25 used Apache 2.4.62 (Debian), Python 3.9.2 and
Chrome 141.0.7390.122. All 30 application tests, including XSS/CSRF browser
checks, and all five integration checks passed. The pinned firmware build
selects Apache 2.4.68. Full
Yocto builds and guest execution were not performed in this session because
Docker daemon access was unavailable; native results do not establish target
package installation, kernel configuration or cross-architecture browser support.
Custom application interpreters (CWE-77), omitted role decisions and range checks
may require analysis rules beyond generic shell/SQL/XSS source-to-sink rules.

</details>

<a id="native-c-path-fixtures-cwe-22-and-cwe-20"></a>

## 📂 C path / filename

Path handling and filename-policy controls.

<details>
<summary>Procedure and technical details</summary>

**Native C path fixtures (CWE-22 and CWE-20)**

These opt-in fixtures cover all eleven [device keywords](#device-keywords), with
**one intentional weakness per firmware**. Device identity and peripheral
specifications are preserved as data; native device daemons, the dashboard,
`iotbench-sim`, and other vulnerability packages are excluded from these minimal
images. The shared image include rejects additional top-level applications and
checks the image manifest for additional CWE packages. Normal catalog builds
skip these 22 images. Other existing benchmark scenarios are unchanged.

| Scenario keyword | Installed native binary | Primary classification | Defect |
| --- | --- | --- | --- |
| `cwe022-native-path-traversal` | `bin/fixture-path-cwe022` | CWE-22; CWE-20 contributes to the same finding | Relative-path syntax is checked, but parent components are not checked against `allowed/` before constructing `allowed/<request>` |
| `cwe020-native-filename-validation` | `bin/fixture-path-cwe020` | CWE-20 only | The filename extension is checked with `strncmp(dot, ".cfg", 4)` without requiring end-of-string |

The installed base is `/usr/share/iotbench/native-path` (or `${datadir}` when
changed by the distro). Implementation and package recipes are under
`meta-iotbench/recipes-vulns/native-path-fixture/`: `files/fixture-path.c` contains
the native services, `files/isolate-path.c` contains the isolation launcher,
`files/fixture-build.py` handles native compilation and target installation,
`files/fixture-runner.py` stages copied runtimes, and `files/test-session.py`
performs the socket assertions. `files/ground-truth.json` records classifications
and expected data flows. `native-path-fixture.inc` compiles the selected branch
with the Yocto cross compiler and preserves normal `${CPPFLAGS}`, `${CFLAGS}`
and `${LDFLAGS}`, adding PIE, stack protection, RELRO, immediate binding and a
non-executable stack. It never disables ASLR or compiler protections.

Each `iotbench-<device>-<scenario>.bb` requires
`recipes-images/iotbench-native-path-fixture.inc`. Only its selected CWE service
is compiled and installed. The optional `-asan` binary instruments that same
variant; it does not add a second vulnerability. Shared source and the ground
truth describe both variants, but preprocessing excludes the other flaw from
the ELF. ELF symbols are retained for analysis, and package stripping/debug
splitting are disabled for these fixtures so `variant.json` hashes remain valid.

### Request interface and data flow

The service listens exclusively at the owner-only Unix-domain socket
`/run/path.sock` **inside the disposable fixture namespace**. No TCP/UDP
listener, HTTP endpoint, shell command, upload, write operation, or boot service
is provided. One request per connection consists of:

1. A two-byte unsigned big-endian pathname length, from 1 through 255.
2. Exactly that many ASCII pathname bytes, without a trailing NUL.
3. A write-side shutdown/EOF from the client.

The response is `OK <decimal-byte-count>\n` followed by exact file contents, or
one of `ERR INVALID\n`, `ERR DENIED\n`, and `ERR MISSING\n`. The response closes
the connection. Truncated frames, trailing bytes/extra frames, absolute paths,
NULs, controls, non-ASCII characters, backslashes and oversized declarations
are rejected. Characters are limited to lowercase ASCII letters, digits, `_`,
`-`, `.`, and `/`; the CWE-20 branch additionally rejects every slash.
Reads and sends have one-second per-connection timeouts; bodies are limited
to 4096 bytes. All copies, framing, pathname construction and responses are
bounded. There is no URL decoding or locale-dependent character validation.

The source-to-sink flow is `request_path()` (socket input) → `retrieve()` →
variant-specific checks/construction → `confined_open()` → Linux `openat2()` →
`fstat()` and `read()` → socket response. Only regular read-only files are
returned. The kernel boundary uses `RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS |
RESOLVE_NO_XDEV`; there is no fallback on older kernels. Symlinks, special files
and mount escapes are not part of either intentional weakness.

### Synthetic resources and intended policies

The runner copies the selected installed artifact into `/fixture`. Its dedicated
synthetic filesystem is then:

```text
CWE-22                            CWE-20
/fixture/fs/                      /fixture/fs/
  allowed/                          allowed/
    public.cfg                        public.cfg
  sentinel.txt                        private.cfg.bak
```

All resources are ordinary 0644 synthetic files in 0755 directories, with a
read-only filesystem during tests. Their source bytes are in `files/assets/`.
`public.cfg` contains `SYNTHETIC_ALLOWED_CONFIGURATION\n`; `sentinel.txt`
contains `SYNTHETIC_CWE22_SENTINEL_ONLY\n`; `private.cfg.bak` contains
`SYNTHETIC_CWE20_DISALLOWED_BACKUP\n`.

For **CWE-22**, the application intends `/fixture/fs/allowed/` as the directory
boundary. Its incomplete syntax check accepts `../sentinel.txt`; the constructed
`allowed/../sentinel.txt` resolves to `/fixture/fs/sentinel.txt`. `openat2()` is
anchored at the *outer* synthetic `fs/` directory, so this violates the intended
application boundary while remaining in the isolated research filesystem.
The sentinel is the only ordinary file outside `allowed/` and is readable by
the service account. This measures containment failure without any OS permission
bypass. CWE-20 describes its contributing validation cause, not another finding.

For **CWE-20**, the explicit contract is the full filename pattern
`[a-z][a-z0-9_-]{0,31}\.cfg`. Prefix length/characters and the absence of slashes
are checked; the terminal extension check is incomplete. `private.cfg.bak`
is therefore returned even though it violates that contract. This is
unauthorized by filename policy, without an authentication or permissions flaw.
The open directory descriptor is `allowed/` itself, and kernel confinement
independently preserves that boundary. No outside sentinel is installed for
this variant.

### Native build and automated tests

Prerequisites: Linux with unprivileged user/mount/network/PID namespaces,
`pivot_root`, proc, tmpfs, and `openat2` (Linux 5.6+), Python 3, `cc`, `readelf`,
and `ldd`. ASan/UBSan require compiler/runtime support. Run as an ordinary
unprivileged user. Tests need permission to create local Unix sockets; an outer
tool sandbox blocking socket creation must allow this isolated regression.
No external network or downloaded dependencies are used.

At the repository root:

```bash
/usr/bin/python3 scripts/test-native-path-fixtures.py --isolated-fixture
/usr/bin/python3 scripts/test-native-path-fixtures.py --isolated-fixture --sanitize
```

The suite compiles real ELF files into fresh disposable artifacts and runs those
staged bytes through the socket interface, including the sanitizer variant when
requested. It checks all 22 image recipes, package/image guards, all five QEMU
machine configurations, target installation from the actual recipe `SRC_URI`,
permissions, unchanged binary hashes, catalog exclusion, wrapper opt-ins, QEMU
network exclusion, production stubs, and ELF hardening. Machine staging checks
reuse host ELF bytes to exercise installation logic; they do **not** establish
execution on those target architectures.

To build and retain a single native artifact for inspection, choose a fresh
output directory (the builder refuses nonempty or symlinked destinations):

```bash
/usr/bin/python3 scripts/build-native-path-fixture.py \
  --output /tmp/iotbench-native-cwe022 --cwe 022 \
  --mode fixture --enable 1 --sanitize
/usr/bin/python3 /tmp/iotbench-native-cwe022/usr/share/iotbench/native-path/fixture-runner.py \
  --isolated-fixture --sanitize
```

Use `--cwe 020` and a different output directory for the other variant.
Omitting either `--mode fixture` or `--enable 1` refuses the build before
creating output. Compiling `fixture-path.c` without
`IOTBENCH_PATH_FIXTURE_ENABLED=1` yields only a disabled exit-77 stub, without
path-handling code. An enabled binary also refuses execution on the host root.

### Build and validate generated firmware artifacts

Choose any device from the device table, and either scenario keyword:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe022-native-path-traversal
FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE=1 yocto
```

Optional target sanitizer build, on toolchains supporting libasan/libubsan:

```bash
FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE=1 \
  -e IOTBENCH_NATIVE_PATH_ASAN=1 yocto
```

The wrapper passes a temporary BitBake configuration enabling only this fixture
family. `IOTBENCH_NATIVE_PATH_ASAN=1` adds `asan` to the selected package's
`PACKAGECONFIG`. Direct BitBake usage requires `IOTBENCH_BUILD_MODE = "fixture"`
and `IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE = "1"` in its test configuration, and
optionally `PACKAGECONFIG:append:pn-cwe022-native-path-traversal = " asan"`
(or the CWE-20 package name). Production mode, absent opt-in, unsupported board
machines, other fixture opt-ins, and mixed vulnerability image packages are
rejected. Kernel namespace options are added only to this opt-in build.

Build exports follow the normal `deploy-images/<firmware>/<machine>/` layout.
Boot using the serial console:

```bash
FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}" scripts/run-qemu.sh
```

The QEMU launcher uses `-nic none`, without forwarding ports or configuring
DHCP. From the guest root serial console, run the tests under the locked,
unprivileged account created by the fixture package:

```bash
su -s /bin/sh -c '/usr/bin/python3 /usr/share/iotbench/native-path/fixture-runner.py --isolated-fixture' iotpath
```

Add `--sanitize` inside that command if the image was built with sanitizer
support. This command **does not compile any service**: it verifies installed
ELF hashes, copies those exact binaries and their runtime libraries, and tests
them in isolation. Run it for both image variants and each architecture being
evaluated. The same runner accepts `--artifact PATH` for an extracted native
artifact on a matching host; foreign-architecture ELFs must run in the guest.
`ldd` is used only on these trusted benchmark binaries and public system runtime
code, not arbitrary untrusted third-party firmware. Hashes detect accidental
packaging changes; they are not authenticity signatures.

### Expected findings and validation evidence

| Case | Expected response/evidence |
| --- | --- |
| Both: `public.cfg` | `OK <length>` and the exact `SYNTHETIC_ALLOWED_CONFIGURATION\n` body, including its byte count |
| CWE-22: `../sentinel.txt` and equivalent relative paths | Exact sentinel contents; resolved outside `allowed/`, inside `fs/` |
| CWE-22: `../../etc/passwd`, proc-root escape, missing sentinel, directory selection | Denied/missing; no other outside resource is returned |
| CWE-20: `private.cfg.bak` | Exact backup contents and an independent full-pattern assertion proving the policy violation |
| CWE-20: traversal, slash, `.bak`, absent extension, digit-leading basename, basename >32 characters | Denied; filename containment checks remain effective |
| Both: missing valid filename | `ERR MISSING` |
| Both: 255-byte path | Bounded filesystem/policy handling; denied/missing |
| Both: empty, truncated, NUL/control/non-ASCII, extra frame, 256/4096/65535-byte declarations | `ERR INVALID`, followed by a successful ordinary request on the same service |
| Both: normal and sanitizer builds | Same semantic results; no AddressSanitizer or UndefinedBehaviorSanitizer diagnostics |
| Production or direct host startup | Refused before creating a listener |

Static analysis should trace socket bytes through `request_path()` to the
read-only `openat2` sink. For CWE-22, report the missing `allowed/` containment
check despite outer `fs/` confinement, with CWE-20 contributing. For CWE-20,
report the missing extension terminator check in `filename_policy()`, without
reporting traversal in that compiled variant. Tools need to model the syscall
wrapper, directory descriptors, and selected preprocessor branch. This fixture
does not promise that a particular scanner implements those models.

The sanitizer check tests unintended address/undefined-behavior errors, while
exact response bytes and independent boundary/pattern assertions establish the
intentional semantic weaknesses. Sanitizer silence alone proves neither a CWE
finding nor the absence of all memory errors. Leak checking is disabled because
the long-running services are terminated by the test harness; address/UB checks
remain enabled, with no recovery after a diagnostic.

### Isolation, cleanup and limits

The non-setuid launcher requires an ordinary caller and explicit
`--isolated-fixture`. It creates user, mount, network, PID, IPC and UTS namespaces,
maps only that caller to UID/GID 1000, and copies staged public runtime files
into a dedicated disposable tmpfs root. It pivots into that root, mounts only
private proc plus tmpfs `/run` and `/tmp`, and detaches the previous host root.
**No host directories, devices, account database or filesystem bind mounts are
retained.** All other inherited file descriptors are closed; stdin is EOF,
capabilities are dropped, and `no_new_privs` is set before tests/services start.
The private network has only a down loopback interface. The synthetic resource
root is read-only; only ephemeral socket/log/tmp state is writable.

Both the test session and service check their isolation prerequisites. Tests
check the four expected mount types, namespace PID 1, UID/GID, capabilities,
read-only resources, absence of the old root and external network interfaces,
and the service's single Unix socket. Resources are reset by copying a fresh
artifact into a new namespace for each run; each service starts fresh, its
socket/log is removed after each test, and resource hashes/modes must remain
unchanged. Namespace exit destroys tmpfs and remaining children; the runner
removes temporary staging directories. A preexisting socket pathname is
preserved and causes startup refusal.

The explicit test manifest, compile guard, package skip, image guard and runtime
isolation checks prevent normal production configuration/startup. The model
covers only small ASCII read-only requests, ordinary synthetic files, and Linux
kernels with the required namespace/openat2 support. There is no host-mode or
older-kernel fallback. These deliberately insecure fixtures are not production
applications. Existing device services and unrelated benchmark weaknesses are
outside their minimal image configuration.

Validation on 2026-10-25 used GCC 10.2.1 and Python 3.9.2. All six integration
checks and six in-namespace cases passed with the ASan/UBSan option, covering
both normal compiled service variants and their instrumented counterparts.
Full Yocto image builds and guest execution were not performed: Docker daemon
access was unavailable in this session. Native tests validate compiled staged
ELFs and installation/build policy, not actual cross-built image installation;
the guest procedure above is required to establish that final evidence.

</details>

<a id="native-c-buffer-overflow-cwe-787-cwe-20-cwe-119"></a>

## 🧠 C buffer overflow

Memory-safety diagnostics and the corrected control.

<details>
<summary>Procedure and technical details</summary>

**Native C buffer overflow (CWE-787, CWE-20, CWE-119)**

### Purpose and integration

Scenario keyword: `cwe787-native-buffer-overflow`. This native C fixture provides
one intentional **CWE-787 out-of-bounds write**, caused by **CWE-20 improper
input validation**, within the broader **CWE-119 memory-bounds category**. These
are classifications of the same defect. The fixture supports source-analysis
evaluation and an expected AddressSanitizer failure; it contains no execution
payload or control-flow manipulation.

All eleven [device keywords](#device-keywords) have an existing
`meta-iotbench/recipes-images/iotbench-<device>-cwe787-native-buffer-overflow.bb`
recipe. Each requires `iotbench-native-buffer-overflow.inc` and installs only
this vulnerability package plus the core boot package group. The selected
`device.conf` and `peripherals.conf` remain available as metadata. Device
applications, daemons and other vulnerability packages are excluded. Nothing
starts this stdin utility automatically; there is no service or network API.
The existing QEMU launcher uses `-nic none` for this family and a disposable
disk overlay by default.

Files relative to the repository root:

| Component | Location |
| --- | --- |
| C source | `meta-iotbench/recipes-vulns/cwe787-native-buffer-overflow/files/fixture-buffer-write.c` |
| Native build targets | `files/Makefile` in the same package: `production` (default), `fixture`, `asan` |
| Cross-build recipe | `meta-iotbench/recipes-vulns/cwe787-native-buffer-overflow/cwe787-native-buffer-overflow_1.0.bb` |
| Image guard and metadata | `meta-iotbench/recipes-images/iotbench-native-buffer-overflow.inc` |
| Host automated tests | `scripts/test-native-buffer-overflow.py` |
| Guest automated tests | Package `files/test-guest.sh`, installed under `/usr/share/iotbench/native-buffer-overflow/` |
| Machine-readable source locations and boundaries | Package `files/ground-truth.json` |

### Data flow and boundaries

One invocation consumes exactly one frame from stdin: a two-byte unsigned
big-endian length, that many printable ASCII bytes (`0x20` through `0x7e`),
then EOF. `read_configuration()` reads the header at source line 23, rejects
lengths above 256 at line 31, and copies at most 256 bytes into the local
`payload[256]`. It rejects truncated headers/bodies, trailing bytes, extra
frames, nonprintable bytes, input errors and extra command-line arguments
before calling the vulnerable function.

The length and payload flow directly to `apply_configuration()`. Its single
missing check is `length <= sizeof(configuration)` before the indexed copy.
The write at **`fixture-buffer-write.c:51`** uses the transport-validated length
to index a smaller **global `unsigned char configuration[64]`**. Length 65
first writes `configuration[64]`. The only subsequent read is explicitly
bounded by both the length and the destination capacity; it cannot introduce
a second out-of-bounds access. The returned checksum is at most `64 * 126`.

| Boundary | Value |
| --- | --- |
| Transport input accepted by parser | 0–256 payload bytes, inclusive |
| Destination capacity / maximum valid configuration | 64 bytes |
| Required string terminator | None: the destination is a length-delimited byte array and is never used as a C string |
| First invalid destination index | 64 |
| Minimum oversized valid frame | 65 printable bytes, header `00 41` |
| First rejected transport length | 257, header `01 01` |

An oversized **valid frame** reaches the intentional defect. A malformed frame
is rejected even if its declared length exceeds 64. Source-analysis tools should
trace `getchar()` → `read_configuration()` → `length`/`payload` →
`apply_configuration()` → `configuration[index] = payload[index]` and identify
the missing destination bound. Scanner-specific detection is not guaranteed.

### Native builds and automated validation

Run from the repository root as an ordinary unprivileged Linux user. Requirements
are Python 3.7+, Make, a C99 compiler supporting AddressSanitizer, its matching
ASan runtime, and binutils (`nm`, `readelf`, plus working source symbolization).
On this workstation `/usr/bin/python3` is Python 3.9; the default `python3` is
older and should not be used for this script.

```bash
/usr/bin/python3 scripts/test-native-buffer-overflow.py --static
/usr/bin/python3 scripts/test-native-buffer-overflow.py --local
```

`--static` checks ground truth, all eleven device recipes, image/package guards
and build wrappers using offline command doubles. `--local` additionally builds
and runs actual native ELFs inside a fresh temporary working directory. The
fixture refuses UID 0, GID 0 and mismatched real/effective IDs. Core dumps are
disabled. Each input executes in a separate subprocess with a five-second
timeout; any timeout fails the test. Temporary artifacts are removed on exit.
This local runner uses temporary directories and ordinary process permissions;
it does not provide a container or namespace sandbox.

To retain a diagnostic build in a disposable directory:

```bash
FIXTURE_SOURCE="$PWD/meta-iotbench/recipes-vulns/cwe787-native-buffer-overflow/files"
FIXTURE_BUILD=$(mktemp -d /tmp/iotbench-buffer.XXXXXX)
make -C "$FIXTURE_SOURCE" BUILD_DIR="$FIXTURE_BUILD" \
  IOTBENCH_BUILD_MODE=fixture IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE=1 asan
/usr/bin/python3 - "$FIXTURE_BUILD/fixture-buffer-write-asan" <<'PY'
import os
import subprocess
import sys
binary = sys.argv[1]
environment = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1:abort_on_error=0:symbolize=1:exitcode=86')
result = subprocess.run([binary], input=b'\x00\x41' + b'A' * 65,
                        cwd=os.path.dirname(binary), env=environment,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
sys.stderr.buffer.write(result.stderr)
assert result.returncode == 86 and not result.stdout
assert b'ERROR: AddressSanitizer: global-buffer-overflow' in result.stderr
assert b'WRITE of size 1' in result.stderr
assert b'fixture-buffer-write.c:51' in result.stderr
PY
rm -r -- "$FIXTURE_BUILD"
```

Use the `fixture` target for a normal enabled ELF, and give it only valid or
malformed inputs. The normal ELF's behavior on oversized valid input is
undefined and is never used as diagnostic evidence. `production`/`all` builds
only `fixture-buffer-write-disabled`, which exits 77 without parsing input.
Compiling the C source directly without `IOTBENCH_BUFFER_FIXTURE_ENABLED=1`
also excludes the vulnerable functions and global destination entirely. Both
`fixture` and `asan` refuse missing opt-in or production mode before creating
output. Native and Yocto builds retain compiler hardening; no protection is
disabled to expose this global-array defect.

### Expected results and diagnostic

For valid configurations, stdout is `OK <length> <checksum>\n` and stderr is
the fixture notice. All cases close stdin after the frame.

| Case | Expected result |
| --- | --- |
| Empty payload, header `00 00` | Exit 0, `OK 0 0` |
| Ordinary payload `A`, header `00 01` | Exit 0, `OK 1 65` |
| Maximum valid payload: 64 `A` bytes, header `00 40` | Exit 0, `OK 64 4160` |
| Oversized valid payload: 65 `A` bytes, header `00 41` | ASan exit 86 with a global-buffer-overflow write report at line 51; no stdout |
| Additional oversized lengths 66, 128 and 256 | Same first invalid store and ASan result |
| Length 257/65535, truncated header/body, surplus data, nonprintable bytes, extra argument | Exit 2, no stdout, notice followed by `ERR INVALID` |
| Default production native build | Exit 77, no stdout, `Native buffer fixture disabled` |

The diagnostic contains the following stable fields; addresses, PIDs, paths
and stack-frame formatting vary by toolchain and ASLR:

```text
ERROR: AddressSanitizer: global-buffer-overflow on address ...
WRITE of size 1 at ...
    #0 ... apply_configuration .../fixture-buffer-write.c:51
...
... global variable 'configuration' ... of size 64
```

The automated regression requires the configured ASan exit code **and** the
global-buffer-overflow classification, write size, destination name and exact
source line. An unexplained signal/crash, timeout, unrelated sanitizer finding
or missing symbols fails. It checks 29 valid inputs and 20 malformed/transport
cases on each of the normal ELF, ASan ELF and temporary repaired control. The
control inserts only the missing destination-length check and must reject
oversized input with `ERR CAPACITY` and no ASan error. It is not another firmware
variant. ASan is the only failure diagnostic exercised; leak detection is
disabled, while address instrumentation and failure-on-first-error remain on.
The tests also verify repeat-build ELF hashes with the same toolchain/paths and
PIE, stack protection, full RELRO and a non-executable stack. Byte-identical
output across different toolchains or checkout paths is not promised.

### Firmware builds and emulated execution

Build a selected image through the existing wrapper:

```bash
FIRMWARE=router-cwe787-native-buffer-overflow docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE=1 yocto
# Optional diagnostic ELF, only where the target toolchain supports ASan:
FIRMWARE=router-cwe787-native-buffer-overflow docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE=1 \
  -e IOTBENCH_NATIVE_BUFFER_ASAN=1 yocto
FIRMWARE=router-cwe787-native-buffer-overflow scripts/run-qemu.sh
```

Replace `router` with any device keyword. The supported QEMU build selectors
remain `qemuarm64`, `qemuarm`, `qemux86-64`, `qemux86`, `qemumips`; set
`YOCTO_MACHINE` when building and booting. ASan runtime support is a separate
toolchain constraint and is not promised on every architecture. Exports retain
`deploy-images/<firmware>/<machine>/`. Leave `QEMU_PERSIST` unset for disposable
guest writes. From the guest root serial console:

```sh
sh /usr/share/iotbench/native-buffer-overflow/test-guest.sh router
# Only if the image includes the optional ASan ELF:
sh /usr/share/iotbench/native-buffer-overflow/test-guest.sh router --asan
```

The guest script checks device identity and installed ELF permissions, creates
a temporary working directory, and runs each utility as UID/GID 65534 with no
supplementary groups and `no_new_privs`. A 15-second timeout covers slower
emulation; a timeout or crash fails. The optional diagnostic case is a separate
process and requires the same ASan fields and exit code as the native tests.
Target ASan tests require sufficient virtual address space and working source
symbolization. Debug information remains in the installed fixture ELFs.
The standard guest smoke checks avoid undefined behavior and do not establish
that ASan works on that architecture. Native ELFs cannot validate execution on
foreign-architecture guests.

Direct BitBake builds require both `IOTBENCH_BUILD_MODE = "fixture"` and
`IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE = "1"` in an explicit test configuration.
Optionally add
`PACKAGECONFIG:append:pn-cwe787-native-buffer-overflow = " asan"`.
Without the two settings, the package is skipped and its dedicated image guard
rejects construction; other images do not select the package. The wrapper
rejects mixed fixture opt-ins. `scripts/build-all.sh` excludes this family by
default; to explicitly include it, set
`IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE=1 IOTBENCH_BUILD_MODE=fixture`, optionally
with `IOTBENCH_NATIVE_BUFFER_ASAN=1`. No external network is used by the native
tests or guest fixture; a first Yocto build may still need the repository's
normal toolchain downloads/cache.

Validation on 2026-10-26 used GCC 10.2.1 and `/usr/bin/python3` 3.9.2. The full
native regression passed, including all eleven device integrations, package
and image policy checks, actual build-wrapper branches with offline doubles,
production stub exclusion, hardening, reproducible rebuild, valid/malformed
inputs, four exact-location ASan failures and the repaired control. Docker
daemon access was denied in this session. Full BitBake parsing, cross-built
image manifests and guest execution were not performed; package/image guard
tests use a minimal datastore double and cannot replace that integration
evidence. The guest commands above remain the required validation for each
emulated target.

</details>

<a id="native-connection-string-injection-cwe-20"></a>

## 🔗 C connection string

Connection-option validation and the corrected control.

<details>
<summary>Procedure and technical details</summary>

**Native connection string injection (CWE-20)**

Scenario keyword: `cwe020-native-connection-string`. The eleven firmware IDs
are `<device>-cwe020-native-connection-string`, for `router`, `ipcamera`,
`smartplug`, `thermostat`, `plc`, `smartbulb`, `smarthub`, `envsensor`,
`smartspeaker`, `healthmonitor` and `doorlock`. They share one native binary,
`/usr/bin/fixture-connection`, and exactly one intentional validation defect.
Each dedicated image retains its device/peripheral metadata and installs the
fixture with the core boot packages, without device application daemons.

Sources and synthetic resource definition are in
[`meta-iotbench/recipes-vulns/cwe020-native-connection-string/files/`](../meta-iotbench/recipes-vulns/cwe020-native-connection-string/files/):
`fixture-connection.c`, `fixture-isolate.h`, `fixture-resource.h`, `Makefile`,
`ground-truth.json`, `NOTICE`, `LICENSE` and `test-guest.sh`. The recipe installs
these assets under `/usr/share/iotbench/native-connection-string/`. There is
no service, socket listener, password or credential file.

### Connector, caller contract and defect

The real connector is the repository's existing `sqlite3` library, using
`sqlite3_open_v2` with `SQLITE_OPEN_URI`. Its documented
[file URI format](https://www.sqlite.org/uri.html) is used here:

```text
file:/tmp/iotbench-connection.<random>/fixture.db?cache=<caller-field>&mode=ro
```

The caller may select the cache value `private` or `shared`. The intended fixed
settings are read-only access (`mode=ro`), the newly generated local database
path, and the built-in Unix VFS. The single defect is the missing exact-value
validation for the cache field: `construct_connection` inserts printable caller
text directly into URI syntax with checked `snprintf`. No query incorporates
this field. All statements, including the final
`SELECT marker FROM fixture_resource WHERE id=1`, are constants.

Data flow is stdin `getchar` → `read_cache` → `field` →
`construct_connection`/`snprintf` → `sqlite3_open_v2` →
`sqlite3_db_readonly(db, "main")` and the fixed SELECT. The existing native stdin
convention is used: two-byte unsigned big-endian length, exactly that many
printable ASCII bytes, then EOF. The transport limit is 256 bytes, backed by a
257-byte terminated field and checked 128-byte path / 512-byte URI buffers.
Percent escapes must encode printable ASCII; malformed escapes, NUL encodings,
non-ASCII encodings and raw nonprintable bytes are rejected before SQLite.
These independent bounds/encoding checks leave the intentional URI syntax
validation defect intact.

The witness `private&mode=rw#` supplies an explicit writable mode and starts a
fragment, so the application's trailing `&mode=ro` is ignored. SQLite reports
`readonly=0`; normal `private` reports `readonly=1`. Both SELECTs return
`SYNTHETIC_CONNECTION_RESOURCE` from the fresh local file. The C API's
`SQLITE_OPEN_READWRITE` flag permits the URI to narrow access to read-only;
`SQLITE_OPEN_CREATE` is absent from the test connection. This fixture models
an application relying on its generated URI for its read-only policy.
Using a read-only API flag would enforce a separate policy and prevent this
witness. See SQLite's [open API rules](https://www.sqlite.org/c3ref/open.html).

### SQLite parsing behavior and limitations

The URI query uses `&` between parameters and `=` between name and value;
`#` begins an ignored fragment. SQL-style single/double quotes and backslashes
do not quote URI values. `%HH` escapes are decoded within parameter components:
`pr%69vate` selects private cache, while `private%23` is an invalid cache value,
not a fragment. Semicolons do not separate parameters.

Duplicate `mode` parameters are processed sequentially in the tested SQLite
3.34.1: `private&mode=rw` followed by the application's `mode=ro` ends read-only;
`private&mode=ro&mode=rw#` fails because it attempts to widen access after
narrowing. Duplicate handling is a tested connector behavior, not a portable
first/last-value rule. The primary witness avoids duplicate query parameters
by moving the fixed suffix into the fragment. Unknown parameters are ignored
by SQLite's core; for example, a synthetic padding parameter can fill the
transport boundary. Tests exercise these cases against the actual linked
library and fail if behavior changes. No connector test double is used.

Only the Unix VFS is registered before input reaches the connector; attempts
to select `unix-none` or an unknown VFS fail. An injected `mode=memory` can select
disposable memory but has no synthetic table and fails the fixed SELECT.
This test does not model server credentials, remote database protocols or
other connectors. Shared-cache support depends on the SQLite build; targets
must support both documented cache choices for the full regression to pass.

### Isolation and resource lifecycle

Each invocation creates a mode-0700 directory using `mkdtemp` under `/tmp`,
with umask 077. `fixture-resource.h` defines the complete synthetic database:
one table and one marker row. Constant initialization SQL creates it, using
memory journals/temp storage, and closes that setup connection before the
caller-controlled URI is parsed. The test connection never creates files or
executes writes. It closes statements and connections, unlinks the database,
removes its directory and shuts down SQLite on both success and parse failure.
No persistent resource or connection state is shared between requests.

The pathname is generated independently of the caller field, and the only
registered VFS is the built-in local Unix backend. A Linux seccomp filter
denies socket creation, connect and program execution; `no_new_privs` is set
and core dumps are disabled. A blocked socket attempt checks that network
confinement is active. Setup fails closed with exit 77 if these restrictions
cannot be installed. Root, group 0 and mismatched real/effective IDs are
refused. The fixture executes no shell commands, loads no extensions and
reads no production credentials. Use a disposable Linux test system: this is
process/syscall isolation with a private resource directory, not a complete
filesystem namespace jail or a sandbox for executing arbitrary hostile code.

Native tests run with a minimal environment and a timeout per request. They
check that temporary resource names and working-directory contents reset after
each case. Ordinary input is rerun after each injection. Compiler fortify,
stack protection, PIE, full RELRO and non-executable stack remain enabled.
The diagnostic build adds ASan and UBSan; its entire input matrix must pass
without sanitizer findings. Leak detection is disabled because LeakSanitizer
cannot use its process-tracing mechanism in this workspace. This does not
disable address or undefined-behavior instrumentation; the system SQLite
library itself is not rebuilt with sanitizers.

### Native build and automated validation

Run from the repository root as an ordinary user on Linux. Requirements:
Python 3.7+, Make, a C99 compiler, SQLite development headers/library, binutils
(`nm`, `readelf`), and matching ASan/UBSan runtimes. Use `/usr/bin/python3` on
this workstation, where the default `python3` is older.

```bash
/usr/bin/python3 scripts/test-native-connection-string.py --static
/usr/bin/python3 scripts/test-native-connection-string.py --local
```

`--static` validates all eleven recipes, package/image production guards,
shell syntax, serial-only QEMU selection and the real build wrappers using
offline command doubles. It does not run Docker or BitBake. `--local` also
builds and tests normal and ASan/UBSan ELFs, verifies hardening and repeat-build
hashes, and creates a temporary repaired control. The control adds only an
exact `private`/`shared` whitelist; normal inputs stay read-only and the
injection is rejected before constructing the URI. This control is not shipped.

For a retained disposable native build and a single witness:

```bash
FIXTURE_SOURCE="$PWD/meta-iotbench/recipes-vulns/cwe020-native-connection-string/files"
FIXTURE_BUILD=$(mktemp -d /tmp/iotbench-connection-build.XXXXXX)
make -C "$FIXTURE_SOURCE" BUILD_DIR="$FIXTURE_BUILD" \
  IOTBENCH_BUILD_MODE=fixture IOTBENCH_ENABLE_CONNECTION_FIXTURE=1 fixture
/usr/bin/python3 - "$FIXTURE_BUILD/fixture-connection" <<'PY'
import subprocess, sys
for field in (b'private', b'private&mode=rw#', b'private'):
    payload = len(field).to_bytes(2, 'big') + field
    subprocess.run([sys.argv[1]], input=payload, check=True, timeout=5)
PY
rm -r -- "$FIXTURE_BUILD"
```

`make` / `make production` creates only `fixture-connection-disabled`, which
exits 77 before parsing input and has no SQLite dependency or fixture parser.
Compiling the C source without `IOTBENCH_CONNECTION_FIXTURE_ENABLED=1` has the
same result. Native `fixture` and `sanitize` targets require both explicit
fixture mode and the enable flag. Production package/image guards refuse this
family; other image recipes do not select it. Repeated native builds are
byte-identical with the same toolchain/source/build paths; equivalence across
different toolchains and checkout paths is not promised.

| Input/control | Expected result |
| --- | --- |
| `private`, `shared`, `pr%69vate` | Exit 0; `OK readonly=1 marker=SYNTHETIC_CONNECTION_RESOURCE` |
| `private&mode=rw#` | Exit 0; same marker, `readonly=0` |
| `private&mode=rw` (no fragment) | Exit 0; `readonly=1` |
| Empty field, `bad`, 256 `A` bytes, quoted cache value, `private%23` | Exit 3; `ERR CONNECT`, no stdout |
| `private&padding=` plus 240 `A` bytes (256 bytes total) | Exit 0; `readonly=1`, same marker |
| `private&mode=ro&mode=rw#`, unknown/removed VFS | Exit 3; `ERR CONNECT`, no stdout |
| `private&mode=memory#` | Exit 3; `ERR RESOURCE`, no stdout |
| Truncated/surplus frame, 257+ length, nonprintable bytes, `%GG`, `%00`, `%FF`, extra argument | Exit 2; `ERR INVALID`, no stdout |
| Disabled native build | Exit 77; disabled message, no stdout |

Enabled runs also emit the installed synthetic fixture notice on stderr.
Source-analysis tools should trace the external field into the connection URI
and flag the missing cache-value validation/encoding as CWE-20. The observable
impact is an unintended writable connection, with fixed SQL and local-only
resource selection. Detection by any particular scanner is not guaranteed.

### Firmware build and guest validation

```bash
FIRMWARE=router-cwe020-native-connection-string docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_CONNECTION_FIXTURE=1 yocto
FIRMWARE=router-cwe020-native-connection-string scripts/run-qemu.sh
# In the disposable guest's root serial console:
sh /usr/share/iotbench/native-connection-string/test-guest.sh router
```

Replace `router` with any supported device. Existing `YOCTO_MACHINE` selectors
and `deploy-images/<firmware>/<machine>/` exports are retained. Leave
`QEMU_PERSIST` unset for disposable guest writes. QEMU starts this family with
no network device. A conditional kernel fragment enables seccomp/filter
support only for explicit fixture builds. Guest checks run the helper with
UID/GID 65534, no supplementary groups and `no_new_privs`, using the installed
cross-built ELF and a 15-second request timeout.

Direct BitBake configuration requires `IOTBENCH_BUILD_MODE = "fixture"` and
`IOTBENCH_ENABLE_CONNECTION_FIXTURE = "1"`. The container wrapper requires the
matching image, rejects production mode/mixed fixture opt-ins and passes a
temporary explicit BitBake configuration. `scripts/build-all.sh` skips this
family unless `IOTBENCH_ENABLE_CONNECTION_FIXTURE=1` is set (use explicit
`IOTBENCH_BUILD_MODE=fixture` as well). The native and guest tests need no
external services or networks; initial Yocto toolchain downloads follow the
repository's existing build/cache workflow.

Validation on 2026-10-26 used GCC 10.2.1, SQLite 3.34.1 and Python 3.9.2.
The complete native regression passed, including both normal and ASan/UBSan
executables, the repaired control, cleanup/reset checks, reproducible rebuild,
hardening, production stub exclusion, eleven device integrations and offline
build-wrapper checks. The existing native buffer fixture's static regression
also passed after the shared wrapper changes. Docker daemon access was denied
and BitBake was unavailable on the
host; full firmware builds, actual image manifests and QEMU guest execution
were not validated here. Datastore/command doubles verify policy and dispatch,
and do not replace cross-build and guest evidence.

</details>

<a id="native-c-symbolic-link-following-cwe-61-and-cwe-59"></a>

## ↪️ C symbolic links

Symbolic-link boundaries and the corrected control.

<details>
<summary>Procedure and technical details</summary>

**Native C symbolic-link following (CWE-61 and CWE-59)**

Scenario keyword: `cwe061-native-symlink-following`. This fixture tests whether
source-analysis tools identify a read-only file open that follows an untrusted
UNIX symbolic link. Its primary classification is **CWE-61 (UNIX Symlink
Following)**, a specific form of **CWE-59 (Improper Link Resolution Before File
Access)**. These describe the same intentional defect, not two vulnerabilities.
The link exists before startup and the request; this fixture introduces no
check/use race, permission bypass, or request-path traversal.

All eleven supported categories have an image named
`iotbench-<device>-cwe061-native-symlink-following.bb`: `router`, `ipcamera`,
`smartplug`, `thermostat`, `plc`, `smartbulb`, `smarthub`, `envsensor`,
`smartspeaker`, `healthmonitor`, and `doorlock`. They retain their device and
peripheral configuration under `/etc/iotbench/`. Like the existing native path
fixtures, they install a minimal boot environment and exactly this vulnerability
package, with no device application daemons or automatically started fixture.

| Component | Repository location |
|---|---|
| Native C source | `meta-iotbench/recipes-vulns/cwe061-native-symlink-following/files/fixture-symlink.c` |
| Binary | `bin/fixture-symlink-cwe061` under the installed artifact |
| Cross-build recipe | `meta-iotbench/recipes-vulns/cwe061-native-symlink-following/cwe061-native-symlink-following_1.0.bb` |
| Image guard and metadata checks | `meta-iotbench/recipes-images/iotbench-native-symlink-fixture.inc` |
| Native build/test entry points | `scripts/build-native-symlink-fixture.py`, `scripts/test-native-symlink-fixture.py` |
| Artifact runner and socket tests | Package `files/fixture-runner.py`, `files/test-session.py` |
| Synthetic resources and analysis labels | Package `files/assets/`, `files/ground-truth.json` |
| Shared namespace launcher | `meta-iotbench/recipes-vulns/native-path-fixture/files/isolate-path.c` |

The installed base is `/usr/share/iotbench/native-symlink` (`${datadir}` is
honored). It includes the C source, shared launcher source, ground truth,
resources, test scripts, and the actual compiled ELF files. Local builds use
the host compiler; Yocto builds use `${CC}`, `${CPPFLAGS}`, `${CFLAGS}` and
`${LDFLAGS}`, then stage those target ELF bytes without recompiling them on the
host. The manifest records this distinction. Staging tests across five machine
names validate artifact layout; they do not emulate other instruction sets.
Stripping/debug splitting are disabled so artifact hashes and analysis symbols
survive packaging. PIE, stack protection, RELRO, immediate binding, and a
non-executable stack are retained; no compiler protections are disabled.

### Policy, layout, and request data flow

The policy requires reading the ordinary `public.cfg` entry in the trusted
`allowed/` directory and rejecting a caller-controlled symlink at that entry.
The harness controls the disposable directory and never replaces its ancestors.
Both ordinary file and sentinel are readable by the service account. All
resources contain only fixed synthetic text.

```text
Read-only artifact resources:           Private writable tmpfs test copy:
/fixture/fs/                           /tmp/symlink-fixture/
  allowed/public.cfg                     allowed/public.cfg
  sentinel.txt                           sentinel.txt

Ordinary: public.cfg contains SYNTHETIC_CWE61_ORDINARY_CONFIGURATION\n
Attack:   allowed/public.cfg -> ../sentinel.txt
Sentinel: sentinel.txt contains SYNTHETIC_CWE61_SENTINEL_ONLY\n
Dangling: allowed/public.cfg -> ../missing-synthetic.txt
```

`test-session.py` copies the resources into the private `/tmp` filesystem. It
replaces only the leaf entry using `unlink()` and `symlink()` before starting
the component. The sentinel remains outside `allowed/`, inside the same
synthetic disposable filesystem. No real system file is an attack target.

The existing local native test interface is used: an AF_UNIX stream socket,
`/run/symlink.sock`, with a two-byte big-endian length followed by exactly
`READ`, then client write EOF. Thus the entire valid wire request is
`00 04 52 45 41 44`. No filename can be supplied. Requests containing
`../sentinel.txt`, absolute paths, appended filenames, NUL bytes, extra frames,
truncation, or oversized declarations return `ERR INVALID\n`.

Data flows through `request_read()` (fixed six-byte bounded parser),
`handle_request()`, `retrieve()`, `openat()`, `fstat()`, and bounded `read()` to
`send_all()`. At startup, the component opens the trusted
`/tmp/symlink-fixture/allowed` directory with `O_DIRECTORY | O_NOFOLLOW` and
pins its descriptor. Each request opens the fixed basename:

```c
openat(rootfd, "public.cfg", O_RDONLY | O_CLOEXEC | O_NONBLOCK | O_NOCTTY);
```

**The single missing safeguard is `O_NOFOLLOW` on this final-component open.**
The kernel follows `public.cfg` to `../sentinel.txt` before returning the file
descriptor. The subsequent `fstat()` verifies that the resolved object is a
regular file of at most 4096 bytes; it cannot detect that the original entry
was a symbolic link. Reads and replies are bounded, descriptors are closed,
and socket operations have timeouts. The service never writes file contents.
For this fixed basename and trusted parent descriptor, adding `O_NOFOLLOW`
would reject the link atomically. A preliminary `lstat()` check would introduce
a separate race and is not used here.

Expected analysis finding: one CWE-61/CWE-59 report on `retrieve()`'s `openat()`
sink, with the caller-controlled filesystem entry as the untrusted source.
This is filesystem-state control rather than tainted request text. A tool
should recognize that a fixed basename, a pinned parent descriptor, and a
post-open regular-file check do not enforce the no-symlink policy. The `..`
inside the synthetic link target illustrates link resolution; it is never a
request-supplied path. Do not label a separate request traversal defect.

### Build and execution

From the repository root, as an ordinary unprivileged Linux user:

```sh
/usr/bin/python3 scripts/test-native-symlink-fixture.py --isolated-fixture

# Optional separate artifact, using a fresh disposable output directory:
/usr/bin/python3 scripts/build-native-symlink-fixture.py \
  --output /tmp/iotbench-cwe061 --mode fixture --enable 1
/usr/bin/python3 /tmp/iotbench-cwe061/usr/share/iotbench/native-symlink/fixture-runner.py \
  --isolated-fixture
```

These native tests use the local C compiler, Python standard library, `ldd`,
`readelf`, and `unshare`, with no downloads or external network access. The
native wrapper builds in a temporary directory and cleans it on completion.
Do not start the service binary directly: it refuses execution outside the
isolated environment with exit status 77.

Build a selected firmware through the existing container workflow:

```sh
FIRMWARE=router-cwe061-native-symlink-following docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE=1 yocto
FIRMWARE=router-cwe061-native-symlink-following ./scripts/run-qemu.sh
```

Replace `router` with any category listed above. `YOCTO_MACHINE` supports
`qemuarm64`, `qemuarm`, `qemux86-64`, `qemux86`, and `qemumips`; normal build
cache/toolchain requirements still apply. In the guest serial console, run:

```sh
su -s /bin/sh -c '/usr/bin/python3 /usr/share/iotbench/native-symlink/fixture-runner.py --isolated-fixture' iotsymlink
```

The test-only account has no elevated privileges. QEMU uses `-nic none` for
this family, including smart-device profiles, and the normal disposable
`-snapshot` behavior. The kernel append conditionally reuses
`native-path-fixture.cfg` for namespace/tmpfs/proc support only in explicitly
enabled fixture mode. No host directories are shared into the guest.

Direct BitBake use requires both `IOTBENCH_BUILD_MODE = "fixture"` and
`IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE = "1"` in the test configuration. The
package is skipped otherwise, and its image guard rejects production mode,
unsupported machines, or unrelated vulnerability packages. The container
wrapper requires the matching firmware selector, rejects mixed fixture flags,
and passes a temporary explicit BitBake configuration. `scripts/build-all.sh`
skips these eleven images unless this family is explicitly enabled. Without
`IOTBENCH_SYMLINK_FIXTURE_ENABLED=1`, the C source compiles only a disabled
exit-77 stub with no fixture file-access implementation.

### Expected and observed validation

| Case | Expected result |
|---|---|
| Ordinary `allowed/public.cfg` | `OK 39\n` followed by exact ordinary synthetic contents |
| Pre-established link to `../sentinel.txt` | `OK 30\n` followed by exact sentinel contents, demonstrating the defect |
| Missing `public.cfg` | `ERR MISSING\n` |
| Dangling symlink | `ERR MISSING\n` |
| Traversal-style input or malformed framing | `ERR INVALID\n`; a subsequent valid request still works |
| Missing runtime flag or execution on host root | Exit 77, no listener |
| Existing socket pathname | Refused without removing or overwriting it |
| Default/production build | Package excluded and native staging rejected |

The harness asserts response contents and the symlink target's inode identity.
It verifies unchanged parent-directory identity and sentinel contents, and
checks descriptor counts across repeated requests. Repeated requests check
resource management; the first attack request must already return the
sentinel, with no scheduling-dependent retries. Cleanup unlinks the entry
itself, including dangling links, then removes known ordinary resources and
empty directories. Socket cleanup occurs after the process exits; namespace
exit discards the tmpfs mounts. The original artifact resources remain
read-only and their contents/modes are checked before and after the run.

Isolation uses the established `isolate-path` launcher and its existing marker:
an unprivileged caller creates private user, mount, PID, network, IPC and UTS
namespaces, copies only ordinary runtime/resource files into a new tmpfs,
pivots root, and detaches the old host filesystem. No host filesystem bind
mount survives. Only the read-only tmpfs root, private proc, writable `/run`,
and writable `/tmp` remain mounted. Service and tests run as UID/GID 1000 in
the namespace, with zero effective/permitted capabilities and `no_new_privs`.
No setuid executable, file capability, root service, or privilege bypass is
required. The harness asserts mounts, credentials, capabilities and network
interfaces before running the request cases.

This runner is Linux-specific and requires unprivileged user namespaces,
mount/pivot-root operations inside those namespaces, private proc/tmpfs,
and AF_UNIX sockets. Restricted containers, LSM policies, or socket-denying
execution sandboxes may block it; it fails instead of falling back to a host
filesystem run. macOS and Windows require a suitable Linux VM. QEMU guest
execution also depends on the guest kernel allowing unprivileged namespaces.
Unlike the older native path fixture, this service does not require `openat2`.

Validation on 2026-10-26: the native suite passed all six outer tests and all
six isolated socket tests. Ordinary, linked, missing, dangling, invalid-input,
runtime-gate and cleanup assertions passed. Integration checks covered eleven
device recipes, five target staging layouts, actual SRC_URI unpacking,
production guards/stub exclusion, compiler protections, rootfs metadata and
integrity rejection, catalog opt-in dispatch, and QEMU network exclusion using
local command doubles. The first sandboxed run was blocked by the workspace
Unix-socket restriction; the passing run retained namespace isolation outside
that restriction. Full Yocto cross-builds and QEMU guest boots have not been
validated here; staging and command doubles do not substitute for that evidence.

The existing native path fixture regression also passed after the shared build-wrapper and kernel-configuration changes (sanitizer cases were not requested). Shell syntax and whitespace checks passed.

</details>

<a id="java-jar-command-injection-cwe-78--cwe-77-contributing-cwe-20"></a>

## ☕ Java command handling

Two synthetic command-handling variants.

<details>
<summary>Procedure and technical details</summary>

**Java JAR command injection (CWE-78 / CWE-77, contributing CWE-20)**

These opt-in fixtures test source and bytecode tracing from a bounded incoming
stdin request to command construction and unintended execution. Each JAR has
one deliberate defect: `FixtureRequest.read()` checks printable ASCII instead
of the documented label alphabet. That incomplete check permits command syntax
to reach its command construction site. CWE-20 describes this contributing
validation failure; there is no redundant CWE-20-only image.

| Variant | Primary classification | Firmware suffix | Executable JAR |
| --- | --- | --- | --- |
| OS shell | CWE-78, broader CWE-77, contributing CWE-20 | `cwe078-java-os-command-injection` | `fixture-os-command.jar` |
| Application interpreter | CWE-77, contributing CWE-20 | `cwe077-java-app-command-injection` | `fixture-app-command.jar` |

The variants use different interpreters and sinks. They are not copies with
different CWE labels. All data and marker values are synthetic; neither
variant installs a service, network listener, boot launcher or interactive shell.

### Device and build integration

All eleven existing categories support Java through the existing OpenJDK layer:
`router`, `ipcamera`, `smartplug`, `thermostat`, `plc`, `smartbulb`, `smarthub`,
`envsensor`, `smartspeaker`, `healthmonitor`, and `doorlock`. Each has two image
recipes, named `iotbench-<device>-<suffix>.bb`. There are no unsupported existing
device categories. These are Linux firmware profiles, including the simulated
sensor and bulb profiles, rather than Java-less microcontroller images.

Sources, resource vectors and ground truth are under
`meta-iotbench/recipes-vulns/java-command-fixture/files/`. Each JAR contains only
`FixtureRequest.class` and its variant's main class. The two package recipes
share `java-command-fixture.inc`; image integration is in
`recipes-images/iotbench-java-command-fixture.inc`. Installed files are ordinary
root-owned 0644 files in `/usr/share/iotbench/java-command-fixture/`. An image
installs only its selected variant, device identity/peripheral configuration,
boot packages, Java and local test dependencies. Device dashboards and protocol
daemons are omitted. The locked `javacommand` test account has UID/GID 991.

The repository pins `openjdk-bin-native` and `openjdk` to 17.x through the
existing `meta-openjdk` layer. Compilation uses `--release 17`, UTF-8, debug
information, `-Xlint:all -Werror`, with no external Java dependencies. No JVM,
compiler, linker, dashboard or system service protections are disabled.
`fixture-build.py` writes sorted, stored ZIP entries with fixed timestamps,
permissions and an executable manifest. Repeated builds with the same compiler
produce identical JAR bytes; different compiler patch versions can differ.
The default machine is `qemuarm64`; other machine/runtime combinations require
their own cross-build and guest verification. Non-Linux hosts cannot use this
namespace harness directly; use an isolated Linux environment.

Build a fixture image explicitly:

```sh
FIRMWARE=router-cwe078-java-os-command-injection docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1 yocto
```

Use `router-cwe077-java-app-command-injection` for the independent interpreter,
or substitute another device. Both package recipes are skipped unless the
build mode is `fixture` and the opt-in is `1`; production mode remains excluded
even with the opt-in set. Image guards reject additional device services or
vulnerability packages in `IMAGE_INSTALL`. The container wrapper rejects mixed
fixture opt-ins and supplies an invocation-local BitBake configuration. No
persistent build configuration is changed. `scripts/build-all.sh` skips these
22 images by default and forwards the opt-in only when explicitly enabled.

Build just the executable artifacts offline (Python >=3.8 and a local JDK >=17):

```sh
python3 scripts/build-java-command-fixture.py --fixture-build --variant os \
  --javac /path/to/jdk-17/bin/javac --output deploy-images/java-command-fixture
python3 scripts/build-java-command-fixture.py --fixture-build --variant app \
  --javac /path/to/jdk-17/bin/javac --output deploy-images/java-command-fixture
cp meta-iotbench/recipes-vulns/java-command-fixture/files/requests.json \
  deploy-images/java-command-fixture/
```

### Request format, data flow and expected results

The application requires both `--fixture-test` and
`IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1`, with its working directory fixed to
`/work`. Send one ASCII request `label=<value>\n`, followed by EOF. The label's
contract is `[A-Za-z0-9_-]{1,128}`. Framing, byte count, field name, encoding,
controls and EOF are checked. Only alphabet validation is intentionally
incomplete: printable spaces, quotes and command separators are accepted.
The byte loop reads at most 136 bytes. The external harness bounds blocking
reads and the lifetime of the entire JVM/process tree.

Normal `label=sensor_01\n` produces exactly `/work/normal.txt`, containing
`sensor_01\n`, in either variant. Here `\n` denotes one LF byte.

For the OS variant, the path is `System.in.read()` → bounded request bytes →
`label` → `FixtureOsCommand.main()` string concatenation →
`new ProcessBuilder("/bin/sh", "-c", command).start()`. The intended command is:

```text
printf '%s\n' '<label>' > normal.txt
```

The shell executable and directory are constants. Its environment contains
only `PATH=/nonexistent` and `LC_ALL=C`; the demonstration uses the POSIX shell
`printf` builtin. There is an explicit shell interpretation step, independent
of any assumptions about `Runtime.exec(String)`.

The `os` request in `requests.json` supplies this label:

```text
sensor' > normal.txt; printf 'JAVA_OS_MARKER\n' > os-marker.txt; #
```

The quote terminates the label; `;` starts a second command and `#` comments
out the remaining template. `/work/normal.txt` contains `sensor\n` and
`/work/os-marker.txt` contains exactly `JAVA_OS_MARKER\n`. The marker is a new
redirection target of a second shell command, demonstrating a structural
change rather than an extra command argument. The control `sensor;mark`
remains quoted in this variant and produces only literal normal output.

For the application variant, `label` reaches `"record " + label`, then
`FixtureAppCommand.interpret()`. Its entire grammar is:

```text
program   := statement (';' statement)*
statement := 'record ' printable-text | 'mark'
```

`printable-text` excludes the semicolon delimiter. There are no escapes,
quoting rules, substitutions, loops or user-selected paths. The interpreter
validates the whole program before execution, permits at most one occurrence
of each operation, and rejects unknown/empty/duplicate statements. `record`
writes its operand to the fixed `normal.txt`; `mark` writes the fixed
`app-marker.txt`, using `CREATE_NEW`. No process APIs are used in this JAR.
The request `label=sensor;mark\n` therefore executes two application commands:
`normal.txt` contains `sensor\n`, and `/work/app-marker.txt` contains exactly
`JAVA_APP_MARKER\n`. The unintended `mark` command establishes CWE-77 without
OS shell execution.

Expected source findings are the missing label-alphabet restriction, string
concatenation across an interpreter boundary, and the corresponding shell or
application sink. Expected bytecode findings include `System.in`/`read`, string
concatenation (`invokedynamic` on JDK 17), `ProcessBuilder.start` only in the
OS JAR, and `String.split`/`interpret`/`Files.writeString` in the application
JAR. The manifest supplies the entry point, and bundled sources plus
`ground-truth.json` identify the exact expected data paths and marker values.
The request framing checks do not neutralize interpreter syntax.

### Isolated automated execution and cleanup

Run the full suite as an unprivileged Linux user:

```sh
python3 scripts/test-java-command-fixture.py --static
python3 scripts/test-java-command-fixture.py --jdk /path/to/jdk-17
```

It requires Python >=3.8, `ldd`, util-linux `unshare`/`setpriv`, procfs and
unprivileged user namespaces. It copies the JDK, required native libraries,
shell, privilege-dropping helper and JARs into a disposable filesystem.
Each execution creates separate user, mount, PID and network namespaces,
changes root into that copy, fixes the working directory to `/work`, then
executes as UID/GID 65534 with every capability removed and
`no_new_privs=1`. A private procfs exposes only namespace processes. No host
directory bind mounts, devices, external interfaces, secrets or network
connections are supplied. The harness checks credentials, capabilities,
PID isolation and loopback-only networking before executing any JAR.
The copied filesystem is disposable; it is not a general-purpose security
boundary for running arbitrary untrusted software or caller-selected tests.

The suite compiles/packages each variant twice, compares bytes, checks Java-17
class versions and executable manifests, and executes `java -jar`. It covers
normal labels, both markers, empty/malformed requests, 1/128/129-byte labels,
oversized input, non-ASCII bytes, controls, runtime opt-out, invalid command
syntax, and the literal shell-metacharacter control. It compares the entire
`/work` directory and file contents, checks that `/tmp` stays empty, resets
state between requests, and tests temporary corrected JARs that restore the
alphabet check and reject both injections.

Each JVM has a ten-second outer timeout, a five-second CPU limit, a 4 KiB
file-size limit and disabled core dumps; the OS fixture also waits at most two
seconds for its shell. The harness kills the process group in `finally` and
uses `unshare --kill-child`: destroying the namespace's init also destroys
remaining descendants. Temporary runtime copies, markers and controls are
removed on success or failure. Missing isolation support fails the test;
there is no host-JVM execution fallback. No package or dependency is fetched
during the tests.

Use `--jar-dir <directory> --variant os` (or `app`) to test an already-built
JAR alongside `requests.json`, including artifacts extracted from a firmware.
This mode performs packaged-runtime checks without compiling corrected
controls or running repository build-dispatch checks.

### Emulated firmware execution and validation limits

`scripts/run-qemu.sh` selects `-nic none`, removes DHCP/forwarding, uses a
throwaway disk overlay by default, and allocates 1 GiB for these fixtures.
The images reserve 512 MiB additional filesystem space for runtime copies.
The opt-in kernel fragment enables user/PID/network namespaces and procfs;
existing hardening remains enabled. Boot a built image:

```sh
FIRMWARE=router-cwe078-java-os-command-injection ./scripts/run-qemu.sh
```

In the guest serial console, use the existing lab console credentials, then
drop privileges before the harness stages or runs the runtime:

```sh
data=/usr/share/iotbench/java-command-fixture
jdk_home=$(dirname "$(dirname "$(readlink -f /usr/bin/java)")")
setpriv --reuid=991 --regid=991 --clear-groups \
  python3 "$data/test-java-command-fixture.py" \
  --jdk "$jdk_home" --jar-dir "$data" --variant os
```

Select `--variant app` in an application fixture image. The package includes
the harness, Python modules, `ldd` and util-linux helpers for these offline
tests. It requires no host shared folders, forwarded ports or external
network. Ensure the guest temporary filesystem has room for the copied
runtime. A namespace-restricting guest policy must fail the test rather than
trigger an unisolated run.

Observed on 2026-10-26: both JARs compiled reproducibly and passed the isolated
packaged-JAR cases on the x86-64 host using Temurin OpenJDK 17.0.8, Debian
OpenJDK 17.0.13 and `/bin/sh` (dash). Both temporary corrected controls rejected injection. Production and
default guards were executed through a minimal BitBake datastore substitute;
catalog dispatch, configuration forwarding and serial-only QEMU arguments
were exercised with local command doubles for all 22 image names. These checks
do not constitute a BitBake image build or guest boot. The full Yocto build
and QEMU runtime have not been executed here: the Docker daemon is inaccessible
to this account and BitBake/QEMU are unavailable. Guest execution additionally
depends on the cross-built runtime, BusyBox `/bin/sh`, target native library
layout and guest kernel namespace policy; those differences remain to be
validated on built images.

</details>

<a id="java-deserialization-cwe-502-with-cwe-20-contributing"></a>

## 📦 Java deserialization

Type validation and callback evidence.

<details>
<summary>Procedure and technical details</summary>

**Java deserialization (CWE-502, with CWE-20 contributing)**

This opt-in fixture evaluates whether source and bytecode analyzers can trace
externally supplied Java serialization bytes into object reconstruction. Its
**one intentional defect** is a missing type allowlist before `readObject()`.
CWE-502 is primary; CWE-20 describes the contributing validation omission and
does not have a duplicate firmware or JAR.

The marker demonstrates unintended callback execution during deserialization;
**it does not establish arbitrary code execution**. There are no third-party
gadget chains, command execution, remote class loading, network operations or
filesystem changes in the callback. The marker only increments a static integer
in the current JVM.

### Device coverage, files and Java requirements

All eleven existing device categories have an opt-in
`iotbench-<device>-cwe502-java-deserialization.bb` image: `router`, `ipcamera`,
`smartplug`, `thermostat`, `plc`, `smartbulb`, `smarthub`, `envsensor`,
`smartspeaker`, `healthmonitor` and `doorlock`. These are the repository's
Linux/Yocto synthetic device profiles; each can install the existing `openjdk`
runtime. No existing device category is excluded. Bare-metal/MCU images,
Java 8/11 runtimes and targets without Java-17 support or unprivileged Linux
user/mount/PID/network namespaces are unsupported by this fixture. Device
category coverage is separate from architecture support: the existing image
launcher lists multiple QEMU architectures, but cross-built Java availability
and runtime behavior must be checked for each machine. This change does not
claim that all architecture combinations were built.

The images preserve device/peripheral metadata while installing only
`packagegroup-core-boot` and `cwe502-java-deserialization` as direct image
packages, with their runtime dependencies. Device daemons and other fixture
packages are excluded by the image guard.

Sources reside in
`meta-iotbench/recipes-vulns/cwe502-java-deserialization/files/`:

| File | Purpose |
| --- | --- |
| `FixtureDeserialize.java` | Executable application, bounded stdin reader, resource filter and late type check |
| `FixtureData.java` | Intended synthetic sensor request, `serialVersionUID = 1` |
| `FixtureMarker.java` | Benchmark-only unexpected class, `serialVersionUID = 1`, counter callback |
| `FixtureHarness.java` | Synthetic serializer, independent counter assertions and corrected allowlist comparison |
| `fixture-build.py` | Offline Java compilation and deterministic JAR packaging |
| `vectors.json` | Expected results and committed base64 normal/marker serialization samples |
| `ground-truth.json` | CWE labels, source/sink/callback and limits for analysis tools |

The application JAR is `fixture-deserialization.jar`; the separate
`fixture-deserialization-tests.jar` contains only the test generator/observer.
Both are installed, alongside sources and test resources, under
`/usr/share/iotbench/java-deserialization-fixture/` in explicitly enabled images.
The application JAR contains exactly the three application/data/marker classes;
it does not contain the test harness. The marker is test-only because the
entire application package is a benchmark fixture, unavailable in production
mode.

Builds use JDK 17 or newer with `javac --release 17 -encoding UTF-8 -g
-Xlint:all -Werror`, matching the existing Java command and SQL fixtures. Yocto
uses `openjdk-bin-native` and installs `openjdk`; no new Java dependency or
build-system dependency is introduced. The Python build script uses only the
standard library, fixed ZIP timestamps, sorted entries and uncompressed ZIP
storage. Rebuilds with the same compiler must be byte-identical; identical
bytecode across different compiler releases is not promised.

### Serialization contract and data flow

The local interface accepts raw Java `ObjectOutputStream` protocol version 5
bytes (header `AC ED 00 05`) on stdin, framed by EOF, with at most 4096 bytes.
It reads one root object; remaining bytes inside that bound are ignored and
are never deserialized. There is no HTTP or other network listener. The
intended root type is `org.iotbench.fixture.deserialization.FixtureData`, whose
fields are a `String sensor` matching `[A-Za-z0-9_-]{1,32}` and an integer
`reading` from -100 through 100. Only synthetic identifiers/readings are used.

The trust boundary is the conversion from externally supplied bytes to live
objects in the fixture JVM:

1. `System.in` enters `FixtureDeserialize.process` and is read into a bounded
   byte array, consuming at most 4097 bytes to detect overflow.
2. A `ByteArrayInputStream` feeds `ObjectInputStream`. The stream filter limits
   bytes to 4096, depth to 8, references to 32 and array length to 16. Any
   existing stream/JVM filter is merged with these restrictions; a rejection
   from either is retained. No global JVM setting or filter factory is changed.
3. `readObject()` reconstructs the root object. The filter intentionally returns
   `UNDECIDED` for otherwise unrestricted types, omitting the intended allowlist.
4. For `FixtureMarker`, reconstruction invokes its private `readObject`, calls
   `defaultReadObject()` and increments the in-memory event counter.
5. The application then checks `instanceof FixtureData`, returns
   `UNEXPECTED_TYPE` for the marker, and cannot undo the callback already run.

The comparison exists only in `FixtureHarness`: it merges an explicit
`FixtureData`/`String` allowlist with the same resource limits and existing
JVM restrictions before reading an object. An unexpected marker is rejected
before its callback; the normal request remains accepted. The intentionally
vulnerable application has no corrected/allowlist runtime mode.

### Build and isolated host validation

From the repository root, use Python >=3.8 and a local JDK >=17. On the
validation host, `python3` resolves to Python 3.6; `/usr/bin/python3` is 3.9.
Adjust the interpreter and JDK path for your machine:

```sh
/usr/bin/python3 scripts/test-java-deserialization-fixture.py --static
/usr/bin/python3 scripts/build-java-deserialization-fixture.py \
  --fixture-build --with-tests \
  --javac /usr/lib/jvm/java-17-openjdk-amd64/bin/javac \
  --output deploy-images/java-deserialization-fixture
/usr/bin/python3 scripts/test-java-deserialization-fixture.py \
  --jdk /usr/lib/jvm/java-17-openjdk-amd64 \
  --output deploy-images/java-deserialization-fixture
```

The full test command also builds both JARs twice and compares their bytes.
`--output` retains the JARs, `vectors.json`, generated `inputs/*.ser` and
`inputs/sha256.json`; without it all artifacts are temporary. Generated normal
and marker streams must match the committed base64 samples. Serialization is
performed locally by `FixtureHarness` using the fixture's own classes, inside
the same isolated runtime used for the application tests. No input is obtained
from external networks. Omitting `--fixture-build` rejects the standalone build.

The runner requires `ldd`, util-linux `unshare`/`setpriv`, procfs and
unprivileged namespaces. It reuses `Sandbox` from
`scripts/test-java-command-fixture.py`; the only shared-helper extension is a
configurable runtime opt-in environment variable. It copies the runtime and
native libraries into a disposable root, adds private procfs and executes
with separate user/mount/PID/network namespaces. There are no host filesystem
bind mounts or shared host folders. Before any fixture Java runs, the runner
verifies UID/GID 65534, zero capabilities, `no_new_privs`, PID isolation and
loopback-only networking with no external route. The host runner itself must
also be unprivileged. Namespace failures stop execution with no unisolated
fallback. This sandbox is intended for these fixed synthetic tests, not for
executing arbitrary software.

Every process has a ten-second wall timeout, a five-second CPU limit, disabled
core dumps and a 4 KiB file-size limit; Java uses a 32 MiB heap and a 512 KiB
stack. Process groups and namespace children are killed on completion or
failure. Marker state is reset between observations, including repeated tests
in the same JVM. The suite checks that `/work` and `/tmp` remain empty.

### Expected and observed results

| Input/control | CLI response / observation |
| --- | --- |
| Normal `FixtureData("sensor_01", 23)` | `OK sensor=sensor_01 reading=23`, exit 0 |
| Unexpected `FixtureMarker` | `UNEXPECTED_TYPE`, exit 2; independent observer sees one callback event |
| Test-harness allowlist with marker | `InvalidClassException` before callback; event count zero |
| Test-harness allowlist with ordinary data | Normal reconstruction succeeds; event count zero |
| Invalid sensor data | `INVALID_DATA`, exit 2 |
| Serialized null | `UNEXPECTED_TYPE`, exit 2 |
| Empty stdin | `EMPTY_INPUT`, exit 2 |
| Truncated header or truncated normal object | `TRUNCATED_STREAM`, exit 2 |
| Invalid stream header | `INVALID_STREAM`, exit 2 |
| 4097 bytes, including a valid marker prefix | `INPUT_TOO_LARGE`, exit 2; observer confirms zero callback events |
| Exactly 4096 bytes with a marker prefix | `UNEXPECTED_TYPE`; the single root object is reconstructed |
| Depth 8 / array length 16 | Resource filter permits reconstruction, then late type check rejects the array root |
| Depth 9 / array length 17 / references over 32 | `FILTER_REJECTED`, exit 2 |
| Existing JVM marker deny rule / stricter depth rule | Remains effective; marker deny rule yields zero callback events |
| Missing environment opt-in or wrong/missing CLI flag | `FIXTURE_DISABLED` on stderr, exit 64, before input is read |

The executable CLI does not print the marker counter. A separate test-harness
process loads the packaged application JAR and calls the same `process` method,
then reads `FixtureMarker.eventCount()` directly. It asserts the counter before
checking the returned error, so `UNEXPECTED_TYPE` alone cannot satisfy the test.
Its allowlist comparison checks the counter even after filter rejection. These
observations repeat with explicit resets and additionally check that oversized
input cannot execute the callback.

Expected source-analysis findings: tainted stdin bytes reach the
`ObjectInputStream.readObject` sink; no type restriction prevents unexpected
classes from being reconstructed; the later `instanceof` check does not protect
against reconstruction callbacks. Bytecode analysis should find the same data
flow, the `readObject` invocation and the marker's private serialization
callback/static counter increment. Resource filtering should not be mistaken
for a type allowlist. Report CWE-502 with contributing CWE-20, with no claim
of arbitrary code execution or third-party gadget exploitation.

Observed on 2026-10-26 using Debian OpenJDK 17.0.13 and Python 3.9.2 on the
x86-64 host: both JARs rebuilt identically; all 16 packaged-JAR input cases
passed in the verified namespace sandbox. Independent callback/allowlist/reset
checks, JVM-filter preservation and runtime opt-in controls passed. Default and
production exclusion gates were executed using a minimal BitBake datastore
substitute. Catalog selection, configuration forwarding and all eleven
serial-only QEMU launch commands passed with command doubles. The existing
Java command-fixture runtime suite also passed after the shared-helper change.
The prebuilt `--jar-dir` workflow passed from a temporary installed directory
without repository sources or compiler invocation.
These checks are not a production image manifest audit or an actual BitBake
image build.

### Firmware build, guest execution and limitations

Explicitly enable the fixture and fixture build mode for the selected image:

```sh
FIRMWARE=router-cwe502-java-deserialization docker compose run --rm \
  -e IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE=1 \
  -e IOTBENCH_BUILD_MODE=fixture yocto
FIRMWARE=router-cwe502-java-deserialization ./scripts/run-qemu.sh
```

Replace `router` with any device keyword listed above. `build-all.sh` skips
these images by default; setting
`IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE=1 IOTBENCH_BUILD_MODE=fixture`
includes them and forwards both settings. The build wrapper rejects mixed
fixture opt-ins or a nonmatching image. The package recipe is skipped in
production/default mode, preventing both application and marker class from
being built or installed; the fixture image independently rejects those modes.
No marker class is added to any production Java application.

The QEMU launcher uses `-nic none`, no DHCP or forwarding, a disposable disk
overlay by default and 1 GiB RAM. The image reserves 512 MiB extra space for
runtime staging and enables the existing opt-in namespace kernel fragment.
There is no autostarted Java service. From the guest serial console, drop to
the fixture account before invoking the runner:

```sh
fixture_data=/usr/share/iotbench/java-deserialization-fixture
fixture_jdk=$(dirname "$(dirname "$(readlink -f /usr/bin/java)")")
setpriv --reuid=992 --regid=992 --clear-groups \
  python3 "$fixture_data/test-java-deserialization-fixture.py" \
  --jdk "$fixture_jdk" --jar-dir "$fixture_data"
```

`--jar-dir` tests the prebuilt application/test JARs and their adjacent
`vectors.json`, without compiling or running repository-only dispatch checks.
It can also test files extracted from an image on an isolated host. Guest
execution needs sufficient temporary space for the runtime copy, target native
library support for staging, and working namespace permissions. A JRE suffices
in this prebuilt mode; compilation needs a JDK.

A full Yocto build and emulated runtime have not been executed here: the Docker
daemon is inaccessible and BitBake/QEMU binaries are unavailable. Host-JVM
results do not establish behavior of a cross-built Java runtime, target library
layout or guest namespace policy. A real production image build/manifest audit
and guest execution remain unverified. Existing stricter JVM filters can
correctly block the intentional demonstration; they must remain enabled.

</details>
