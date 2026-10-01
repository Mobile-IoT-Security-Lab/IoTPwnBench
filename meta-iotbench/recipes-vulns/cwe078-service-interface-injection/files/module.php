<?php
declare(strict_types=1);

dashboard_register_module([
    'id' => 'service-injection',
    'title' => 'Service Interface',
    'tag' => 'SERVICE',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="service_probe">
    <label>Probe
        <input name="probe" value="status; id" maxlength="160" required>
    </label>
    <button class="button primary" type="submit">Probe localhost:9090</button>
    <pre class="module-output" aria-live="polite">No probe yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'service_probe' => static function (array $input): array {
            $probe = trim((string)($input['probe'] ?? 'status'));
            $sock = @stream_socket_client('tcp://127.0.0.1:9090', $errno, $errstr, 2);
            if (!$sock) {
                return ['ok' => false, 'error' => 'Service unavailable: ' . $errstr, 'status' => 503];
            }
            fwrite($sock, $probe . "\n");
            stream_set_timeout($sock, 2);
            $out = stream_get_contents($sock);
            fclose($sock);
            return ['ok' => true, 'message' => 'Service probed', 'output' => trim((string)$out)];
        },
    ],
]);
