<?php
declare(strict_types=1);

dashboard_register_module([
    'id' => 'ssh-backdoor',
    'title' => 'SSH Support Backdoor',
    'tag' => 'AUTH',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="ssh_backdoor_check">
    <label>Account
        <input name="user" value="support" maxlength="32" required>
    </label>
    <button class="button primary" type="submit">Check account</button>
    <pre class="module-output" aria-live="polite">No check yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'ssh_backdoor_check' => static function (array $input): array {
            $user = preg_replace('/[^a-z0-9_-]/', '', (string)($input['user'] ?? 'support')) ?: 'support';
            $passwd = '';
            foreach (@file('/etc/passwd') ?: [] as $line) {
                if (strncmp($line, $user . ':', strlen($user) + 1) === 0) {
                    $passwd = $line;
                    break;
                }
            }
            return ['ok' => true, 'message' => 'Backdoor account checked', 'output' => trim((string)@file_get_contents('/etc/iotbench/backdoor-note')) . "\n\n/etc/passwd: " . trim($passwd)];
        },
    ],
]);
