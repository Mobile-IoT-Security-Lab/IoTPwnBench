<?php
declare(strict_types=1);

// Corrected variant of CWE-798. No credential is shipped in the firmware. The
// support account is enrolled per device in a root-provisioned file that holds
// the user name and a password hash, and support access is off until then.
const IOTBENCH_SUPPORT_CREDENTIALS = '/etc/iotbench/support.credentials';
const IOTBENCH_SUPPORT_BACKUP = '/usr/share/iotbench/hardcoded-credentials/support-backup.json';

function hardcoded_credentials_backup(array $input): array
{
    $username = $input['username'] ?? '';
    $password = $input['password'] ?? '';
    if (!is_string($username) || !is_string($password) ||
        strlen($username) > 64 || strlen($password) > 128) {
        return ['ok' => false, 'error' => 'Invalid credential format', 'status' => 422];
    }
    $enrolled = @file_get_contents(IOTBENCH_SUPPORT_CREDENTIALS);
    $parts = $enrolled === false ? [] : explode(':', trim($enrolled), 2);
    if (count($parts) !== 2 || $parts[0] === '' || $parts[1] === '') {
        return ['ok' => false, 'error' => 'Support access is not provisioned', 'status' => 503];
    }
    if (!hash_equals($parts[0], $username) || !password_verify($password, $parts[1])) {
        return ['ok' => false, 'error' => 'Invalid support credentials', 'status' => 401];
    }

    // Only authenticated requests can export this maintenance-only fixture.
    // It lives outside the document root; a client cannot select another file.
    $raw = @file_get_contents(IOTBENCH_SUPPORT_BACKUP);
    $maintenance = $raw === false ? null : json_decode($raw, true);
    if (!is_array($maintenance)) {
        return ['ok' => false, 'error' => 'Support backup unavailable', 'status' => 500];
    }
    $device = dashboard_device();
    $backup = [
        'device' => $device,
        'maintenance' => $maintenance,
        'settings' => dashboard_state(),
        'peripherals' => dashboard_sim(),
    ];
    return [
        'ok' => true,
        'message' => 'Support backup exported',
        'authenticated_as' => $parts[0],
        'device' => $device['class'],
        'signal' => 'HARDCODED_CREDENTIALS_ACCEPTED',
        'backup' => $backup,
        'output' => "HARDCODED_CREDENTIALS_ACCEPTED\n" .
            json_encode($backup, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES),
    ];
}

dashboard_register_module([
    'id' => 'hardcoded-credentials',
    'title' => 'Vendor Support Backup',
    'tag' => 'MAINTENANCE',
    'render' => static function (): string {
        return <<<'HTML'
<p>Sign in with your vendor support account to export the device maintenance backup.</p>
<form class="module-form" data-action="support_backup">
    <label>Support username
        <input name="username" autocomplete="username" maxlength="64" required>
    </label>
    <label>Support password
        <input name="password" type="password" autocomplete="current-password" maxlength="128" required>
    </label>
    <button class="button primary" type="submit">Export support backup</button>
    <pre class="module-output" aria-live="polite">No backup exported yet.</pre>
</form>
HTML;
    },
    'actions' => ['support_backup' => 'hardcoded_credentials_backup'],
]);
