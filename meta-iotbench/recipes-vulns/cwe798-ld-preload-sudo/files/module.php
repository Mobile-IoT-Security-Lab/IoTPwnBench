<?php
declare(strict_types=1);

dashboard_register_module([
    'id' => 'ldpreload',
    'title' => 'LD_PRELOAD Sudo',
    'tag' => 'PRIVILEGE',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="ldpreload_run">
    <label>Preload library
        <input name="library" value="/usr/lib/iotbench/preload-marker.so" maxlength="160" required>
    </label>
    <button class="button primary" type="submit">Run sudo target</button>
    <pre class="module-output" aria-live="polite">No run yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'ldpreload_run' => static function (array $input): array {
            $library = trim((string)($input['library'] ?? '/usr/lib/iotbench/preload-marker.so'));
            $process = @proc_open(
                ['sudo', '-n', 'LD_PRELOAD=' . $library, '/usr/bin/ldpreload-target'],
                [1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
                $pipes
            );
            if (!is_resource($process)) {
                return ['ok' => false, 'error' => 'Could not start sudo', 'status' => 500];
            }
            $out = stream_get_contents($pipes[1]) . stream_get_contents($pipes[2]);
            fclose($pipes[1]);
            fclose($pipes[2]);
            $code = proc_close($process);
            $marker = @file_get_contents('/tmp/iotbench-ldpreload-root') ?: 'marker not written';
            return ['ok' => true, 'message' => 'Sudo target finished', 'output' => trim($out) . "\nexit=" . $code . "\n" . $marker];
        },
    ],
]);
