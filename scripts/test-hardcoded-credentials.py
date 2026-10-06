#!/usr/bin/env python3
"""Verify CWE-798 support backup authentication against a booted firmware."""

import argparse
from html.parser import HTMLParser
import json
import urllib.error
import urllib.request


class TokenParser(HTMLParser):
    token = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "meta" and attributes.get("name") == "dashboard-token":
            self.token = attributes.get("content")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def verify(base, device):
    with urllib.request.urlopen(base + "/", timeout=10) as response:
        page = response.read().decode()
    parser = TokenParser()
    parser.feed(page)
    require(parser.token, "Dashboard token not found")
    require('data-action="support_backup"' in page, "Support backup panel missing")
    require("iotbench-support-2026" not in page, "Password leaked in public HTML")

    def operation(fields, status, token=parser.token):
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["X-Dashboard-Token"] = token
        request = urllib.request.Request(
            base + "/api.php",
            data=json.dumps({"action": "support_backup", **fields}).encode(),
            headers=headers,
        )
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            result = json.load(response)
            require(response.status == status,
                    f"Expected HTTP {status}, got {response.status}: {result}")
        require(result.get("ok") is (status == 200), f"Wrong result: {result}")
        if status != 200:
            require("backup" not in result and "HARDCODED_CREDENTIALS_ACCEPTED" not in
                    json.dumps(result), f"Rejected request exposed backup: {result}")
        return result

    credentials = {"username": "support", "password": "iotbench-support-2026"}
    operation(credentials, 403, token=None)
    operation(credentials, 403, token="invalid-token")
    print("PASS dashboard panel and request-token enforcement")

    for fields in (
        {},
        {"username": "support"},
        {"password": credentials["password"]},
        {"username": "support", "password": "incorrect"},
        {"username": "admin", "password": credentials["password"]},
        {"username": "support", "password": credentials["password"] + " "},
        {"username": "support", "password": "' OR '1'='1"},
    ):
        operation(fields, 401)
    for fields in (
        {"username": ["support"], "password": credentials["password"]},
        {"username": "support", "password": {"value": credentials["password"]}},
        {"username": "A" * 65, "password": credentials["password"]},
        {"username": "support", "password": "A" * 129},
    ):
        operation(fields, 422)
    print("PASS missing, incorrect, injection-shaped and malformed credentials rejected")

    for _ in range(2):
        result = operation(credentials, 200)
        require(result.get("authenticated_as") == "support", "Wrong support account")
        require(result.get("signal") == "HARDCODED_CREDENTIALS_ACCEPTED",
                "Missing exploitation signal")
        backup = result.get("backup", {})
        require(result.get("device") == device and
                backup.get("device", {}).get("class") == device,
                f"Wrong device identity: {result}")
        require(backup.get("maintenance", {}).get("backup_scope") == "vendor-support-only"
                and backup["maintenance"].get("inventory_reference") == "IOTBENCH-SUPPORT-LAB",
                "Protected maintenance fixture missing")
        require("lan_ip" in backup.get("settings", {}), "Device settings missing")
        require(bool(backup.get("peripherals")), "Live simulated peripherals missing")
    # A previous successful request must not authorize a later anonymous one.
    operation({}, 401)
    print(f"PASS {device}: shared firmware credential exports maintenance backup on repeated requests")

    with urllib.request.urlopen(base + "/api.php", timeout=10) as response:
        public = json.load(response)
    require("backup" not in public and "IOTBENCH-SUPPORT-LAB" not in json.dumps(public),
            "Public telemetry exposed maintenance backup")
    for path in (
        "/support-backup.json",
        "/usr/share/iotbench/hardcoded-credentials/support-backup.json",
        "/modules/hardcoded-credentials/module.php",
    ):
        try:
            with urllib.request.urlopen(base + path, timeout=10) as response:
                raise AssertionError(f"Private firmware file served over HTTP: {path}")
        except urllib.error.HTTPError as error:
            require(error.code == 404, f"Unexpected response for {path}: {error.code}")
            error.close()
    print("PASS maintenance files outside web root and no persistent authentication bypass")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--device", required=True, help="expected device class, e.g. router or plc")
    args = parser.parse_args()
    verify(args.url.rstrip("/"), args.device)


if __name__ == "__main__":
    main()
