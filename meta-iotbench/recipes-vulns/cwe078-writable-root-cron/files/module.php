<?php
declare(strict_types=1);

const CRON_SCRIPT = '/var/lib/router-dashboard/cron-maintenance.sh';

dashboard_register_module([
    'id' => 'writable-cron',
    'title' => 'Writable Root Cron Script',
    'tag' => 'PRIVILEGE',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="cron_overwrite">
    <label>Script body
        <input name="body" value="id > /tmp/iotbench-cron-root" maxlength="180" required>
    </label>
    <button class="button primary" type="submit">Overwrite script</button>
    <pre class="module-output" aria-live="polite">No write yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'cron_overwrite' => static function (array $input): array {
            $body = trim((string)($input['body'] ?? 'id > /tmp/iotbench-cron-root'));
            if ($body === '' || strlen($body) > 180) {
                return ['ok' => false, 'error' => 'Invalid script body', 'status' => 422];
            }
            $script = "#!/bin/sh\n" . $body . "\n";
            $ok = @file_put_contents(CRON_SCRIPT, $script, LOCK_EX);
            @chmod(CRON_SCRIPT, 0775);
            return ['ok' => $ok !== false, 'message' => $ok !== false ? 'Cron script overwritten' : 'Write failed', 'output' => (string)@file_get_contents(CRON_SCRIPT)];
        },
    ],
]);
