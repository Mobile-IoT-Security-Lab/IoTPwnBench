<?php
declare(strict_types=1);

dashboard_register_module([
    'id' => 'bash-injection',
    'title' => 'Shell Diagnostics',
    'tag' => 'DIAGNOSTICS',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="bash_diag">
    <label>Target
        <input name="target" value="127.0.0.1; id" maxlength="160" required>
    </label>
    <button class="button primary" type="submit">Run diagnostic</button>
    <pre class="module-output" aria-live="polite">No run yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'bash_diag' => static function (array $input): array {
            $target = trim((string)($input['target'] ?? ''));
            $process = @proc_open(['/usr/bin/iotbench-netdiag', $target], [1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes);
            if (!is_resource($process)) {
                return ['ok' => false, 'error' => 'Could not start diagnostic', 'status' => 500];
            }
            $out = stream_get_contents($pipes[1]) . stream_get_contents($pipes[2]);
            fclose($pipes[1]);
            fclose($pipes[2]);
            $code = proc_close($process);
            return ['ok' => true, 'message' => 'Diagnostic complete', 'output' => trim($out) . "\nexit=" . $code];
        },
    ],
]);
