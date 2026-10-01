<?php
declare(strict_types=1);

dashboard_register_module([
    'id' => 'uaf',
    'title' => 'Session Cache',
    'tag' => 'MEMORY',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="uaf_run">
    <label>Replacement object
        <input name="payload" value="role=admin;device=router" maxlength="60" required>
    </label>
    <button class="button primary" type="submit">Replay session</button>
    <pre class="module-output" aria-live="polite">No replay yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'uaf_run' => static function (array $input): array {
            $payload = substr((string)($input['payload'] ?? ''), 0, 60);
            $process = @proc_open(['/usr/bin/iotbench-uaf', $payload], [1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes);
            if (!is_resource($process)) {
                return ['ok' => false, 'error' => 'Could not start helper', 'status' => 500];
            }
            $out = stream_get_contents($pipes[1]) . stream_get_contents($pipes[2]);
            fclose($pipes[1]);
            fclose($pipes[2]);
            $code = proc_close($process);
            return ['ok' => true, 'message' => 'Replay complete', 'output' => trim($out) . "\nexit=" . $code];
        },
    ],
]);
