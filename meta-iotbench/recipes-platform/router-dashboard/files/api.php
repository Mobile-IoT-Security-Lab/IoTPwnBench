<?php
declare(strict_types=1);

require '/usr/share/router-dashboard/router.php';

header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header('Referrer-Policy: no-referrer');

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if ($method === 'GET') {
    $state = dashboard_state();
    dashboard_json([
        'ok' => true,
        'state' => $state,
        'metrics' => dashboard_live_metrics(),
        'clients' => dashboard_clients($state),
        'sim' => dashboard_sim(),
    ]);
}

if ($method !== 'POST') {
    header('Allow: GET, POST');
    dashboard_json(['ok' => false, 'error' => 'Method not supported'], 405);
}

$token = $_SERVER['HTTP_X_DASHBOARD_TOKEN'] ?? '';
if (!is_string($token) || !hash_equals(dashboard_csrf_token(), $token)) {
    dashboard_json(['ok' => false, 'error' => 'Invalid request token'], 403);
}

$raw = file_get_contents('php://input');
if ($raw === false || strlen($raw) > 32768) {
    dashboard_json(['ok' => false, 'error' => 'Invalid request'], 400);
}
$input = json_decode($raw, true);
if (!is_array($input)) {
    dashboard_json(['ok' => false, 'error' => 'Invalid JSON'], 400);
}

$action = (string)($input['action'] ?? '');
$state = dashboard_state();
$message = 'Settings updated';

switch ($action) {
    case 'save_wifi':
        $ssid = dashboard_clean_text($input['ssid'] ?? '', 32);
        $guestSsid = dashboard_clean_text($input['guest_ssid'] ?? '', 32);
        $security = (string)($input['security'] ?? '');
        $channel = (int)($input['channel'] ?? 0);
        if ($ssid === '' || $guestSsid === '') {
            dashboard_json(['ok' => false, 'error' => 'The network name cannot be empty'], 422);
        }
        if (!in_array($security, ['WPA2-Personal', 'WPA3-Personal', 'WPA2/WPA3 Mixed'], true)) {
            dashboard_json(['ok' => false, 'error' => 'Invalid security mode'], 422);
        }
        if (!in_array($channel, [36, 40, 44, 48, 149, 153, 157, 161], true)) {
            dashboard_json(['ok' => false, 'error' => 'Invalid Wi-Fi channel'], 422);
        }
        $state['ssid'] = $ssid;
        $state['guest_ssid'] = $guestSsid;
        $state['security'] = $security;
        $state['channel'] = $channel;
        $state['wifi_enabled'] = (bool)($input['wifi_enabled'] ?? false);
        $state['guest_enabled'] = (bool)($input['guest_enabled'] ?? false);
        if (trim((string)($input['password'] ?? '')) !== '') {
            if (strlen((string)$input['password']) < 8) {
                dashboard_json(['ok' => false, 'error' => 'The password must be at least 8 characters long'], 422);
            }
            // The simulator intentionally never persists the submitted secret.
            $state['wifi_key_configured'] = true;
        }
        $state['last_event'] = 'Wi-Fi configuration updated';
        $message = 'Wi-Fi configuration saved';
        break;

    case 'save_network':
        $name = dashboard_clean_text($input['router_name'] ?? '', 32);
        $lanIp = dashboard_clean_text($input['lan_ip'] ?? '', 15);
        $start = dashboard_clean_text($input['dhcp_start'] ?? '', 15);
        $end = dashboard_clean_text($input['dhcp_end'] ?? '', 15);
        if ($name === '' || !dashboard_valid_ipv4($lanIp) || !dashboard_valid_ipv4($start) || !dashboard_valid_ipv4($end)) {
            dashboard_json(['ok' => false, 'error' => 'Invalid router name or IPv4 address'], 422);
        }
        $state['router_name'] = $name;
        $state['lan_ip'] = $lanIp;
        $state['dhcp_start'] = $start;
        $state['dhcp_end'] = $end;
        $state['dhcp_enabled'] = (bool)($input['dhcp_enabled'] ?? false);
        $state['last_event'] = 'LAN configuration updated';
        $message = 'Network configuration saved';
        break;

    case 'client_access':
        $mac = strtoupper((string)($input['mac'] ?? ''));
        if (!preg_match('/^([0-9A-F]{2}:){5}[0-9A-F]{2}$/', $mac)) {
            dashboard_json(['ok' => false, 'error' => 'Invalid MAC address'], 422);
        }
        $blocked = array_values(array_unique(array_map('strtoupper', (array)($state['blocked_clients'] ?? []))));
        if ((bool)($input['blocked'] ?? false)) {
            if (!in_array($mac, $blocked, true)) {
                $blocked[] = $mac;
            }
            $message = 'Device paused';
        } else {
            $blocked = array_values(array_filter($blocked, static fn(string $item): bool => $item !== $mac));
            $message = 'Device access restored';
        }
        $state['blocked_clients'] = $blocked;
        $state['last_event'] = $message;
        break;

    case 'restart':
        $state['last_event'] = 'Simulated restart requested';
        $state['restart_requested_at'] = gmdate('c');
        $message = 'Simulated restart: no system command was executed';
        break;

    default:
        // Dispatch to a vulnerability module that registered this action.
        foreach (dashboard_modules() as $module) {
            $handler = $module['actions'][$action] ?? null;
            if (is_callable($handler)) {
                $result = $handler($input);
                $ok = (bool)($result['ok'] ?? true);
                $status = (int)($result['status'] ?? ($ok ? 200 : 400));
                unset($result['status']);
                dashboard_json($result, $status);
            }
        }
        dashboard_json(['ok' => false, 'error' => 'Unknown action'], 400);
}

if (!dashboard_save($state)) {
    dashboard_json(['ok' => false, 'error' => 'Could not save the settings'], 500);
}

dashboard_json([
    'ok' => true,
    'message' => $message,
    'state' => $state,
    'clients' => dashboard_clients($state),
]);
