<?php
declare(strict_types=1);

dashboard_register_module([
    'id' => 'vi-privesc',
    'title' => 'Privileged vi',
    'tag' => 'PRIVILEGE',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="vi_sudo_check">
    <label>File argument
        <input name="file" value="/tmp/iotbench-vi.txt" maxlength="120" required>
    </label>
    <button class="button primary" type="submit">Check sudo rule</button>
    <pre class="module-output" aria-live="polite">No check yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'vi_sudo_check' => static function (array $input): array {
            $file = trim((string)($input['file'] ?? '/tmp/iotbench-vi.txt'));
            $cmd = 'sudo -n -l /bin/busybox vi ' . escapeshellarg($file) . ' 2>&1';
            $out = shell_exec($cmd) ?: '';
            return ['ok' => true, 'message' => 'Sudo rule checked', 'output' => trim($out)];
        },
    ],
]);
