<?php
declare(strict_types=1);

function java_configuration_lookup(array $input): array
{
    $record = $input['record_name'] ?? null;
    if (!is_string($record) || $record === '' || strlen($record) > 960 ||
        str_contains($record, "\0") || preg_match('//u', $record) !== 1) {
        return ['ok' => false, 'error' => 'Invalid record name', 'status' => 422];
    }
    // Fixed loopback backend and raw request body. No shell, process execution,
    // user-selected URL, SQL construction, or SQL escaping in this adapter.
    $context = stream_context_create(['http' => [
        'method' => 'POST',
        'header' => "Content-Type: text/plain; charset=utf-8\r\nConnection: close\r\n",
        'content' => $record,
        'timeout' => 6,
        'ignore_errors' => true,
        'follow_location' => 0,
    ]]);
    $output = @file_get_contents('http://127.0.0.1:18089/lookup', false, $context, 0, 8192);
    $status = 0;
    foreach ($http_response_header ?? [] as $header) {
        if (preg_match('/^HTTP\/\S+ (\d{3})/', $header, $match)) {
            $status = (int)$match[1];
            break;
        }
    }
    if ($output === false || $status === 0) {
        return ['ok' => false, 'error' => 'Configuration service unavailable', 'status' => 503];
    }
    if ($status !== 200) {
        return ['ok' => false, 'error' => $status === 422 || $status === 413
            ? 'Invalid record name' : 'Configuration lookup failed',
            'status' => $status === 422 || $status === 413 ? 422 : 400];
    }
    return [
        'ok' => true,
        'message' => $output === '' ? 'No public configuration found' : 'Configuration lookup complete',
        'device' => dashboard_device()['class'],
        'output' => $output,
    ];
}

dashboard_register_module([
    'id' => 'java-configuration-lookup',
    'title' => 'Configuration Lookup',
    'tag' => 'MAINTENANCE',
    'render' => static function (): string {
        return <<<'HTML'
<p>Look up public configuration records by name. Internal records are reserved for firmware maintenance.</p>
<form class="module-form" data-action="java_configuration_lookup">
    <label>Record name
        <input name="record_name" value="public" maxlength="240" required>
    </label>
    <button class="button primary" type="submit">Search configuration</button>
    <pre class="module-output" aria-live="polite">No lookup performed yet.</pre>
</form>
HTML;
    },
    'actions' => ['java_configuration_lookup' => 'java_configuration_lookup'],
]);
