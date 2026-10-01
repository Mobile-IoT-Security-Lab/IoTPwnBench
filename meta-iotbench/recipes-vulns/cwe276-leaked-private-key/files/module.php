<?php
declare(strict_types=1);

dashboard_register_module([
    'id' => 'leaked-key',
    'title' => 'Leaked Private Key',
    'tag' => 'SECRETS',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="leaked_key_check">
    <label>Public path
        <input name="path" value="/debug/device-private.key" maxlength="120" required>
    </label>
    <button class="button primary" type="submit">Fetch</button>
    <pre class="module-output" aria-live="polite">No fetch yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'leaked_key_check' => static function (array $input): array {
            $path = '/' . ltrim((string)($input['path'] ?? '/debug/device-private.key'), '/');
            $full = '/www/pages' . $path;
            $data = @file_get_contents($full);
            if ($data === false) {
                return ['ok' => false, 'error' => 'Key not readable', 'status' => 404];
            }
            return ['ok' => true, 'message' => 'Key fetched', 'output' => $data];
        },
    ],
]);
