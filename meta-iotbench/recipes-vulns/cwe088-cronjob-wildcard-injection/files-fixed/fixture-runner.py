#!/usr/bin/env python3
"""Execute one fixed, inert fixture schedule by expanding argv without a shell."""

import argparse
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess

MANIFEST = 'IOTBENCH_CRON_WILDCARD_TEST_ONLY_V1\nmode=fixture\nenabled=1\n'


def regular(path, executable=False):
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or mode & 0o022 or (executable and mode & 0o6000):
        raise ValueError('Expected protected regular fixture file: ' + str(path))


def run_once(root, secure=False):
    # Corrected twin: the installed schedule always separates operands with --.
    secure = True
    root = Path(root)
    if not root.is_absolute() or root != root.resolve():
        raise ValueError('Use the absolute canonical fixture root')
    for directory in (root, root / 'bin', root / 'cron', root / 'logs'):
        mode = directory.lstat().st_mode
        if not stat.S_ISDIR(mode) or mode & 0o022:
            raise ValueError('Fixture control directory must be protected')
    inbox = root / 'inbox'
    if not stat.S_ISDIR(inbox.lstat().st_mode):
        raise ValueError('Inbox must be a real fixture directory')
    marker = root / 'build-config'
    helper = root / 'bin/fixture-maintenance'
    regular(marker)
    regular(helper, executable=True)
    if marker.read_text() != MANIFEST:
        raise ValueError('Explicit fixture build marker required')
    config = root / 'cron' / ('secure.crontab' if secure else 'vulnerable.crontab')
    regular(config)
    entries = [line for line in config.read_text().splitlines()
               if line.strip() and not line.startswith('#')]
    if len(entries) != 1:
        raise ValueError('Exactly one fixed fixture schedule required')
    fields = entries[0].split(None, 6)
    expected = ['cd', str(inbox), '&&', str(helper), '--fixture-test']
    if secure:
        expected.append('--')
    expected.append('*')
    if fields[:6] != ['*/5', '*', '*', '*', '*', 'root'] or len(fields) != 7:
        raise ValueError('Unexpected fixture schedule or simulated role')
    if shlex.split(fields[6]) != expected:
        raise ValueError('Only the fixed fixture command is supported')

    # Equivalent to the bare shell glob in the declared cwd. Names remain argv
    # strings, never shell source. Dotfiles are excluded; unmatched * stays '*'.
    names = sorted(name for name in os.listdir(str(inbox)) if not name.startswith('.'))
    args = [str(helper), '--fixture-test'] + (['--'] if secure else []) + (names or ['*'])
    result = subprocess.run(args, cwd=str(inbox), stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, timeout=10,
                            env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'})
    if result.returncode:
        raise ValueError('Fixture helper refused context: ' + result.stderr.strip())
    events = [json.loads(line) for line in result.stdout.splitlines()]
    # Create a new log without following/replacing existing links or files.
    log = root / 'logs' / ('secure.jsonl' if secure else 'vulnerable.jsonl')
    fd = os.open(str(log), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(result.stdout)
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--secure', action='store_true')
    parser.add_argument('--isolated-fixture', action='store_true', required=True)
    args = parser.parse_args()
    try:
        events = run_once(args.root, args.secure)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    for event in events:
        print(json.dumps(event, sort_keys=True))


if __name__ == '__main__':
    main()
