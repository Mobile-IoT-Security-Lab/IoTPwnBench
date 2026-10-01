<?php
declare(strict_types=1);

dashboard_register_module([
    'id' => 'diagnostic-dos',
    'title' => 'Resource Diagnostic',
    'tag' => 'AVAILABILITY',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="dos_run">
    <label>Megabytes
        <input name="megabytes" value="128" maxlength="6" required>
    </label>
    <button class="button primary" type="submit">Allocate</button>
    <pre class="module-output" aria-live="polite">No allocation yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'dos_run' => static function (array $input): array {
            $mb = preg_replace('/[^0-9]/', '', (string)($input['megabytes'] ?? '1')) ?: '1';
            $process = @proc_open(['/usr/bin/iotbench-dos', $mb], [1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes);
            if (!is_resource($process)) {
                return ['ok' => false, 'error' => 'Could not start helper', 'status' => 500];
            }
            $out = stream_get_contents($pipes[1]) . stream_get_contents($pipes[2]);
            fclose($pipes[1]);
            fclose($pipes[2]);
            $code = proc_close($process);
            return ['ok' => true, 'message' => 'Allocation attempted', 'output' => trim($out) . "\nexit=" . $code];
        },
    ],
]);
