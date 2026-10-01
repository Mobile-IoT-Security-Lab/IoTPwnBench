<?php
declare(strict_types=1);

const BAD_CHOWN_FILE = '/etc/iotbench/wan-policy.conf';

dashboard_register_module([
    'id' => 'bad-chown',
    'title' => 'Writable WAN Policy',
    'tag' => 'PERMISSIONS',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="bad_chown_write">
    <label>Policy line
        <input name="line" value="DNS_OVERRIDE=attacker-controlled" maxlength="120" required>
    </label>
    <button class="button primary" type="submit">Write policy</button>
    <pre class="module-output" aria-live="polite">No write yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'bad_chown_write' => static function (array $input): array {
            $line = trim((string)($input['line'] ?? ''));
            if ($line === '' || strlen($line) > 120) {
                return ['ok' => false, 'error' => 'Invalid policy line', 'status' => 422];
            }
            $ok = @file_put_contents(BAD_CHOWN_FILE, $line . "\n", FILE_APPEND | LOCK_EX);
            $stat = @stat(BAD_CHOWN_FILE);
            return [
                'ok' => $ok !== false,
                'message' => $ok !== false ? 'Policy modified as routerweb' : 'Write failed',
                'output' => "target=" . BAD_CHOWN_FILE . "\nuid=" . ($stat['uid'] ?? 'n/a') . " gid=" . ($stat['gid'] ?? 'n/a') . "\n\n" . (string)@file_get_contents(BAD_CHOWN_FILE),
            ];
        },
    ],
]);
