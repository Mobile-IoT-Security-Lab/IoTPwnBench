<?php
declare(strict_types=1);

function weak_cipher_run(array $input): array
{
    $operation = $input['operation'] ?? 'encrypt';
    $data = $input['data'] ?? '';
    if (!is_string($operation) || !in_array($operation, ['encrypt', 'decrypt'], true) ||
        !is_string($data) || strlen($data) > ($operation === 'encrypt' ? 4096 : 8298)) {
        return ['ok' => false, 'error' => 'Invalid operation or input size', 'status' => 422];
    }
    $process = @proc_open(
        ['/usr/bin/iotbench-weak-cipher', $operation],
        [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
        $pipes
    );
    if (!is_resource($process)) {
        return ['ok' => false, 'error' => 'Could not start encryption helper', 'status' => 500];
    }
    $written = fwrite($pipes[0], $data);
    fclose($pipes[0]);
    $output = stream_get_contents($pipes[1]);
    $error = stream_get_contents($pipes[2]);
    fclose($pipes[1]);
    fclose($pipes[2]);
    $code = proc_close($process);
    if ($code !== 0 || $written !== strlen($data) || $output === false) {
        return ['ok' => false, 'error' => trim((string)$error) ?: 'Cipher operation failed', 'status' => 422];
    }
    $result = $operation === 'encrypt' ? rtrim($output, "\n") : $output;
    // JSON and the dashboard accept text; binary plaintext remains available via CLI.
    if (preg_match('//u', $result) !== 1) {
        return ['ok' => false, 'error' => 'Plaintext is not UTF-8; use the guest CLI for binary data', 'status' => 422];
    }
    return [
        'ok' => true,
        'message' => ucfirst($operation) . ' complete',
        'cipher' => '3DES-CBC',
        'block_bits' => 64,
        'result' => $result,
        'output' => "cipher=3DES-CBC\nblock_bits=64\n" . $result,
    ];
}

dashboard_register_module([
    'id' => 'weak-cipher',
    'title' => 'Device Backup Encryption',
    'tag' => 'CRYPTOGRAPHY',
    'render' => static function (): string {
        return <<<'HTML'
<p>Encrypt or restore device backup text using Triple DES (3DES-CBC) with a fixed firmware key and IV.</p>
<form class="module-form" data-action="weak_cipher">
    <label>Operation
        <select name="operation"><option value="encrypt">Encrypt</option><option value="decrypt">Decrypt</option></select>
    </label>
    <label>Backup text or encrypted frame
        <textarea name="data" rows="5" maxlength="8298">{"backup":"device-settings","profile":"lab"}</textarea>
    </label>
    <button class="button primary" type="submit">Process backup</button>
    <pre class="module-output" aria-live="polite">No backup processed yet.</pre>
</form>
HTML;
    },
    'actions' => ['weak_cipher' => 'weak_cipher_run'],
]);
