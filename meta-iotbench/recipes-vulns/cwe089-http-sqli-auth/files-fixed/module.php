<?php
declare(strict_types=1);

const SQLI_DB = '/var/lib/router-dashboard/auth.db';

function sqli_auth_init(): void
{
    if (is_file(SQLI_DB)) {
        return;
    }
    $sql = "CREATE TABLE users(username TEXT, password TEXT, role TEXT);"
         . "INSERT INTO users VALUES('admin','correct-horse','admin');"
         . "INSERT INTO users VALUES('viewer','viewer','viewer');";
    $process = @proc_open(['sqlite3', SQLI_DB, $sql], [1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes);
    if (is_resource($process)) {
        fclose($pipes[1]);
        fclose($pipes[2]);
        @proc_close($process);
    }
    @chown(SQLI_DB, 'routerweb');
    @chmod(SQLI_DB, 0640);
}

dashboard_register_module([
    'id' => 'sqli-auth',
    'title' => 'HTTP Login',
    'tag' => 'WEB',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="sqli_login">
    <label>Username
        <input name="username" value="admin" maxlength="80" required>
    </label>
    <label>Password
        <input name="password" value="' OR '1'='1" maxlength="120" required>
    </label>
    <button class="button primary" type="submit">Login</button>
    <pre class="module-output" aria-live="polite">No login yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'sqli_login' => static function (array $input): array {
            sqli_auth_init();
            $username = (string)($input['username'] ?? '');
            $password = (string)($input['password'] ?? '');
            $quote = static fn (string $value): string => "'" . str_replace(["'", "\0"], ["''", ''], $value) . "'";
            $sql = "SELECT role FROM users WHERE username = " . $quote($username) . " AND password = " . $quote($password) . ";";
            $process = @proc_open(['sqlite3', SQLI_DB, $sql], [1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes);
            if (!is_resource($process)) {
                return ['ok' => false, 'error' => 'sqlite3 unavailable', 'status' => 500];
            }
            $out = stream_get_contents($pipes[1]) . stream_get_contents($pipes[2]);
            fclose($pipes[1]);
            fclose($pipes[2]);
            $code = proc_close($process);
            return ['ok' => true, 'message' => 'Login query executed', 'output' => "SQL: " . $sql . "\nexit=" . $code . "\nrole=" . trim($out)];
        },
    ],
]);
