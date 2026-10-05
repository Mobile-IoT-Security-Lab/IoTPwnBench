#!/usr/bin/env python3
"""Exercise the weak-cipher dashboard on a running IoTBench firmware."""
from html.parser import HTMLParser
import json
import sys
import urllib.error
import urllib.request


class TokenParser(HTMLParser):
    token = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "meta" and attributes.get("name") == "dashboard-token":
            self.token = attributes.get("content")


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080").rstrip("/")
    with urllib.request.urlopen(base + "/", timeout=10) as response:
        page = response.read().decode()
    parser = TokenParser()
    parser.feed(page)
    assert parser.token, "Dashboard token not found"
    assert 'data-action="weak_cipher"' in page, "Weak-cipher panel not installed"

    def operation(mode, data, success=True):
        request = urllib.request.Request(
            base + "/api.php",
            data=json.dumps({"action": "weak_cipher", "operation": mode, "data": data}).encode(),
            headers={"Content-Type": "application/json", "X-Dashboard-Token": parser.token},
        )
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            result = json.load(response)
            assert result.get("ok") is success, result
            assert (response.status == 200) is success, response.status
        return result

    for plain in ("", "device-settings ; id", "Temperatura 21°C", "A" * 4096):
        encrypted = operation("encrypt", plain)
        assert encrypted["cipher"] == "3DES-CBC" and encrypted["block_bits"] == 64
        assert encrypted["result"].startswith("3DES-CBC:")
        assert operation("decrypt", encrypted["result"])["result"] == plain
    first = operation("encrypt", "same backup")["result"]
    second = operation("encrypt", "same backup")["result"]
    assert first == second, "Hardcoded key and IV must give deterministic output"
    # Reference frame made independently with OpenSSL and the documented constants.
    expected = (
        "3DES-CBC:1234567890abcdef26d494330e8c051518ce777b8d9a9b0e"
        "32395f7f07b95178f6c42af4c9acf7f802eab2fa5bec8344dddc10e03595ff8f"
    )
    assert first == expected, "Firmware does not use the documented keys and IV"
    assert bytes.fromhex(first.split(":", 1)[1])[:8].hex() == "1234567890abcdef"
    assert operation("decrypt", first)["result"] == "same backup"
    altered = first[:-1] + ("0" if first[-1] != "0" else "1")
    operation("decrypt", altered, success=False)
    operation("decrypt", "3DES-CBC:00", success=False)
    operation("encrypt", "A" * 4097, success=False)
    operation("invalid", "backup", success=False)
    print("PASS: HTTP panel, 3DES round trips, hardcoded key/IV, deterministic frames and input limits")


if __name__ == "__main__":
    main()
