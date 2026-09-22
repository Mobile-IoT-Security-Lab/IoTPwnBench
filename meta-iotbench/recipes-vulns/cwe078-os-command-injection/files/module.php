<?php
declare(strict_types=1);

/*
 * CWE-78 OS command injection module.
 *
 * The 'ping' action passes the submitted target to /usr/bin/router-ping, which
 * builds a shell command from it without sanitization. Intentionally vulnerable;
 * lab use only. The fix is to validate the target as an IPv4 address and invoke
 * ping with a direct argument vector (no shell).
 */

dashboard_register_module([
    'id' => 'ping',
    'title' => 'Ping',
    'tag' => 'DIAGNOSTICS',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="ping">
    <label>Target
        <input name="target" maxlength="240" placeholder="e.g. 192.168.8.1" required>
    </label>
    <button class="button primary" type="submit">Run ping</button>
    <pre class="module-output" aria-live="polite">No test run yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'ping' => static function (array $input): array {
            $target = trim((string)($input['target'] ?? ''));
            if ($target === '' || strlen($target) > 240) {
                return ['ok' => false, 'error' => 'Invalid target', 'status' => 422];
            }
            // Unsanitized input reaches the shell inside router-ping (CWE-78).
            $process = @proc_open(
                ['/usr/bin/router-ping', $target],
                [1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
                $pipes
            );
            if (!is_resource($process)) {
                return ['ok' => false, 'error' => 'Could not start the diagnostic', 'status' => 500];
            }
            $stdout = stream_get_contents($pipes[1]);
            $stderr = stream_get_contents($pipes[2]);
            fclose($pipes[1]);
            fclose($pipes[2]);
            $exitCode = proc_close($process);

            return [
                'ok' => true,
                'message' => 'Ping test complete',
                'output' => trim((string)$stdout . (string)$stderr),
                'exit_code' => $exitCode,
            ];
        },
    ],
]);
