<?php
declare(strict_types=1);

const REPORT_DIR = '/var/lib/router-dashboard/reports/';

dashboard_register_module([
    'id' => 'path-traversal',
    'title' => 'Report Viewer',
    'tag' => 'FILES',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="read_report">
    <label>Report
        <input name="report" value="../../../../etc/passwd" maxlength="180" required>
    </label>
    <button class="button primary" type="submit">Open report</button>
    <pre class="module-output" aria-live="polite">No report opened yet.</pre>
</form>
HTML;
    },
    'actions' => [
        'read_report' => static function (array $input): array {
            $report = trim((string)($input['report'] ?? 'status.txt'));
            $path = REPORT_DIR . $report;
            $data = @file_get_contents($path);
            if ($data === false) {
                return ['ok' => false, 'error' => 'Report not readable', 'status' => 404];
            }
            return ['ok' => true, 'message' => 'Report opened', 'output' => "path=" . $path . "\n\n" . $data];
        },
    ],
]);
