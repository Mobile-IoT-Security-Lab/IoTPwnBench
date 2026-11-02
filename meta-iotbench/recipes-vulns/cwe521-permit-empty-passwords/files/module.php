<?php
declare(strict_types=1);

// A closed synthetic policy fixture, not a general OpenSSH configuration parser.
function ssh_password_policy_parse(string $text): ?array
{
    $expected = [
        'permitemptypasswords' => 'yes',
        'passwordauthentication' => 'yes',
        'permitrootlogin' => 'no',
        'kbdinteractiveauthentication' => 'no',
        'usepam' => 'no',
        'hostbasedauthentication' => 'no',
        'ignorerhosts' => 'yes',
        'strictmodes' => 'yes',
        'permituserenvironment' => 'no',
        'allowagentforwarding' => 'no',
        'allowtcpforwarding' => 'no',
        'x11forwarding' => 'no',
        'permittunnel' => 'no',
        'listenaddress' => '127.0.0.1',
    ];
    $policy = [];
    foreach (explode("\n", $text) as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#') {
            continue;
        }
        if (preg_match('/\A([A-Za-z][A-Za-z0-9]*)[ \t]+([^ \t\r\n#]+)[ \t]*(?:#.*)?\z/', $line, $match) !== 1) {
            return null;
        }
        $key = strtolower($match[1]);
        $value = $match[2];
        if (!array_key_exists($key, $expected) || array_key_exists($key, $policy)) {
            return null;
        }
        if ($key === 'permitemptypasswords') {
            if (!in_array($value, ['yes', 'no'], true)) {
                return null;
            }
        } elseif ($value !== $expected[$key]) {
            return null;
        }
        $policy[$key] = $value;
    }
    return count($policy) === count($expected) ? $policy : null;
}

function ssh_password_policy_run(array $input): array
{
    $mode = array_key_exists('policy', $input) ? $input['policy'] : 'firmware';
    $password = array_key_exists('password', $input) ? $input['password'] : '';
    if (!is_string($mode) || !in_array($mode, ['firmware', 'corrected'], true) ||
        !is_string($password) || strlen($password) > 128 || strpos($password, "\0") !== false) {
        return ['ok' => false, 'error' => 'Invalid policy or candidate password', 'status' => 422];
    }

    // The request cannot choose a configuration path or change the installed file.
    $text = @file_get_contents('/etc/ssh/sshd_config', false, null, 0, 4097);
    $policy = is_string($text) && strlen($text) <= 4096 ? ssh_password_policy_parse($text) : null;
    if ($policy === null) {
        return ['ok' => false, 'error' => 'Installed policy is not a supported fixture configuration', 'status' => 500];
    }
    if ($mode === 'corrected') {
        $policy['permitemptypasswords'] = 'no';
    }

    // This is a policy diagnostic only: no identity, account or session is created.
    $empty = $password === '';
    $permitted = !$empty || $policy['permitemptypasswords'] === 'yes';
    $decision = $empty
        ? ($permitted ? 'POLICY_PERMITS_EMPTY_PASSWORD' : 'POLICY_REJECTS_EMPTY_PASSWORD')
        : 'POLICY_PERMITS_NONEMPTY_PASSWORD';
    $output = "diagnostic=synthetic\npolicy={$mode}\n" .
        "PermitEmptyPasswords={$policy['permitemptypasswords']}\n" .
        "PasswordAuthentication={$policy['passwordauthentication']}\n" .
        "PermitRootLogin={$policy['permitrootlogin']}\n" .
        'password_empty=' . ($empty ? 'yes' : 'no') . "\ndecision={$decision}";
    return [
        'ok' => true,
        'message' => 'Password policy checked',
        'policy' => $mode,
        'password_empty' => $empty,
        'permitted_by_policy' => $permitted,
        'decision' => $decision,
        'output' => $output,
    ];
}

dashboard_register_module([
    'id' => 'ssh-empty-password-policy',
    'title' => 'SSH Password Policy',
    'tag' => 'AUTHENTICATION',
    'render' => static function (): string {
        return <<<'HTML'
<p>Compare the installed SSH password policy with a corrected control. This is a synthetic policy check; it does not sign you in or open an SSH session.</p>
<form class="module-form" data-action="ssh_password_policy">
    <label>Policy
        <select name="policy"><option value="firmware">Installed firmware</option><option value="corrected">Corrected control</option></select>
    </label>
    <label>Candidate password
        <input name="password" type="password" maxlength="128" autocomplete="off" placeholder="Leave empty to test the empty-password policy">
    </label>
    <button class="button primary" type="submit">Check password policy</button>
    <pre class="module-output" aria-live="polite">No policy check performed yet.</pre>
</form>
HTML;
    },
    'actions' => ['ssh_password_policy' => 'ssh_password_policy_run'],
]);
