#!/usr/bin/env python3
"""Verify anonymous FTP access and its boundaries against a booted firmware."""

import argparse
import ftplib
import io
import json


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def denied(operation, description):
    try:
        operation()
    except ftplib.error_perm as error:
        require(str(error).startswith(("500", "502", "530", "550", "553")),
                f"Unexpected rejection for {description}: {error}")
    else:
        raise AssertionError(f"Unexpected permission: {description}")


def retrieve(ftp, filename):
    result = io.BytesIO()
    ftp.retrbinary(f"RETR {filename}", result.write)
    return result.getvalue()


def verify(host, port, device):
    for username in ("anonymous", "ftp"):
        with ftplib.FTP(timeout=10) as ftp:
            ftp.connect(host, port)
            # USER alone must log in: sending PASS would hide a password prompt.
            reply = ftp.sendcmd(f"USER {username}")
            require(reply.startswith("230"), f"Passwordless login failed: {reply}")
            require(ftp.pwd() == "/", "Anonymous session is not at its FTP root")
            files = ftp.nlst()
            require({"README.txt", "device.conf", "peripherals.conf", "settings.json"}
                    <= set(files), f"Incomplete backup listing: {files}")
            identity = retrieve(ftp, "device.conf").decode()
            if device:
                require(f'DEVICE_CLASS="{device}"' in identity,
                        f"Wrong device identity: {identity}")
            require(bool(retrieve(ftp, "peripherals.conf")), "Empty peripheral backup")
            settings = json.loads(retrieve(ftp, "settings.json"))
            require(isinstance(settings, dict) and "lan_ip" in settings,
                    "Backup does not contain device network settings")
            denied(lambda: ftp.storbinary("STOR anonymous-test.txt", io.BytesIO(b"test")),
                   "anonymous upload")
            denied(lambda: ftp.mkd("anonymous-test"), "anonymous directory creation")
            denied(lambda: ftp.delete("settings.json"), "anonymous backup deletion")
            denied(lambda: retrieve(ftp, "/etc/passwd"), "read outside the FTP root")
            require(json.loads(retrieve(ftp, "settings.json")) == settings,
                    "Rejected writes changed the backup")
            ftp.quit()
        print(f"PASS {username}: passwordless login, listing, backup download, access boundaries")

    with ftplib.FTP(timeout=10) as ftp:
        ftp.connect(host, port)
        denied(lambda: ftp.login("root", "routeradmin"), "local root FTP login")
    print("PASS local account login rejected")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2121)
    parser.add_argument("--device", help="expected device class, e.g. router or plc")
    args = parser.parse_args()
    verify(args.host, args.port, args.device)


if __name__ == "__main__":
    main()
