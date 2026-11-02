"""Offline checks for the configuration-only SSH fixture; never starts sshd."""

from pathlib import Path
import shlex

# A deliberately closed configuration: reject Include, Match, duplicates and
# unreviewed changes rather than pretending to implement the OpenSSH parser.
POLICY = {
    'permitemptypasswords': 'yes',
    'passwordauthentication': 'yes',
    'permitrootlogin': 'no',
    'kbdinteractiveauthentication': 'no',
    'usepam': 'no',
    'hostbasedauthentication': 'no',
    'ignorerhosts': 'yes',
    'strictmodes': 'yes',
    'permituserenvironment': 'no',
    'allowagentforwarding': 'no',
    'allowtcpforwarding': 'no',
    'x11forwarding': 'no',
    'permittunnel': 'no',
    'listenaddress': '127.0.0.1',
}


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_config(path, expected='yes'):
    """Validate the entire fixture policy and return whether it is vulnerable."""
    check(expected in ('yes', 'no'), 'Expected yes or no')
    actual = {}
    for line in Path(path).read_text().splitlines():
        words = shlex.split(line, comments=True)
        if not words:
            continue
        check(len(words) == 2, f'Unsupported configuration line: {line}')
        key, value = words[0].lower(), words[1]
        check(key in POLICY, f'Unexpected directive: {key}')
        check(key not in actual, f'Duplicate directive: {key}')
        actual[key] = value
    wanted = dict(POLICY, permitemptypasswords=expected)
    check(actual == wanted, f'Fixture policy mismatch: {actual}')
    return actual['permitemptypasswords'] == 'yes'


def validate_rootfs(rootfs):
    """Check a generated, extracted rootfs without executing any guest code."""
    root = Path(rootfs)
    config = root / 'etc/ssh/sshd_config'
    check(config.is_file() and not config.is_symlink(), 'Missing regular sshd_config')
    check(config.stat().st_mode & 0o022 == 0, 'sshd_config is writable by group/others')
    check(validate_config(config), 'Missing vulnerable policy')
    panel = root / 'usr/share/router-dashboard/modules/ssh-empty-password-policy/module.php'
    check(panel.is_file() and not panel.is_symlink(), 'Missing regular SSH policy dashboard module')
    check(panel.stat().st_mode & 0o022 == 0, 'SSH policy module is writable by group/others')
    for path in root.rglob('*'):
        name = path.name.lower()
        check(not (name in ('sshd', 'sshd-session', 'sshd-auth', 'dropbear',
                            'dropbearmulti', 'tinysshd', 'lshd')
                   or name.startswith(('sshd.', 'ssh.socket', 'ssh.service',
                                       'dropbear.', 'sshd@', 'ssh@'))
                   or (path.parent.name == 'init.d' and ('ssh' in name or 'dropbear' in name))),
              f'SSH server binary or startup entry present: {path}')
    # Read only: the fixture never changes either authentication database.
    for filename in ('passwd', 'shadow'):
        path = root / 'etc' / filename
        check(path.is_file(), f'Missing authentication database: {filename}')
        for line in path.read_text().splitlines():
            if not line or line.startswith('#'):
                continue
            fields = line.split(':')
            check(len(fields) >= 2 and fields[1] != '',
                  f'Empty password field in {filename}: {fields[0]}')
    return True
