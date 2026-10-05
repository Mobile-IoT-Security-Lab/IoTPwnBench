<?php
declare(strict_types=1);

// This fallback models a proxy/application normalization mismatch: lighttpd
// decodes the URL once and the dispatcher decodes it again before mapping it.
$requestPath = (string)(parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?? '/');
$decodedPath = rawurldecode(rawurldecode($requestPath));
$reportPath = '/var/lib/router-dashboard/reports/' . ltrim($decodedPath, '/');
$contents = @file_get_contents($reportPath);

header('Content-Type: text/plain; charset=utf-8');
if ($contents === false) {
    http_response_code(404);
    echo "report not found\n";
    exit;
}

http_response_code(200);
echo $contents;
