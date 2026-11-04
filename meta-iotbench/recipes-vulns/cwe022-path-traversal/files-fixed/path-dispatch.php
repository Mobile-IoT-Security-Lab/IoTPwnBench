<?php
declare(strict_types=1);

// The dispatcher decodes the path once and serves only files below the reports directory.
$requestPath = (string)(parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?? '/');
$decodedPath = rawurldecode($requestPath);
$reportPath = '/var/lib/router-dashboard/reports/' . ltrim($decodedPath, '/');
$reportsRoot = realpath('/var/lib/router-dashboard/reports');
$resolved = realpath($reportPath);
$inside = $reportsRoot !== false && $resolved !== false
    && strncmp($resolved, $reportsRoot . '/', strlen($reportsRoot) + 1) === 0;
$contents = $inside ? @file_get_contents($resolved) : false;

header('Content-Type: text/plain; charset=utf-8');
if ($contents === false) {
    http_response_code(404);
    echo "report not found\n";
    exit;
}

http_response_code(200);
echo $contents;
