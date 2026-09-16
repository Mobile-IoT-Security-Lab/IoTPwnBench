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
    ]);
}

if ($method !== 'POST') {
    header('Allow: GET, POST');
    dashboard_json(['ok' => false, 'error' => 'Metodo non supportato'], 405);
}

$token = $_SERVER['HTTP_X_DASHBOARD_TOKEN'] ?? '';
if (!is_string($token) || !hash_equals(dashboard_csrf_token(), $token)) {
    dashboard_json(['ok' => false, 'error' => 'Token richiesta non valido'], 403);
}

$raw = file_get_contents('php://input');
if ($raw === false || strlen($raw) > 32768) {
    dashboard_json(['ok' => false, 'error' => 'Richiesta non valida'], 400);
}
$input = json_decode($raw, true);
if (!is_array($input)) {
    dashboard_json(['ok' => false, 'error' => 'JSON non valido'], 400);
}

$action = (string)($input['action'] ?? '');
$state = dashboard_state();
$message = 'Impostazioni aggiornate';

switch ($action) {
    case 'save_wifi':
        $ssid = dashboard_clean_text($input['ssid'] ?? '', 32);
        $guestSsid = dashboard_clean_text($input['guest_ssid'] ?? '', 32);
        $security = (string)($input['security'] ?? '');
        $channel = (int)($input['channel'] ?? 0);
        if ($ssid === '' || $guestSsid === '') {
            dashboard_json(['ok' => false, 'error' => 'Il nome della rete non può essere vuoto'], 422);
        }
        if (!in_array($security, ['WPA2-Personal', 'WPA3-Personal', 'WPA2/WPA3 Mixed'], true)) {
            dashboard_json(['ok' => false, 'error' => 'Modalità di sicurezza non valida'], 422);
        }
        if (!in_array($channel, [36, 40, 44, 48, 149, 153, 157, 161], true)) {
            dashboard_json(['ok' => false, 'error' => 'Canale Wi-Fi non valido'], 422);
        }
        $state['ssid'] = $ssid;
        $state['guest_ssid'] = $guestSsid;
        $state['security'] = $security;
        $state['channel'] = $channel;
        $state['wifi_enabled'] = (bool)($input['wifi_enabled'] ?? false);
        $state['guest_enabled'] = (bool)($input['guest_enabled'] ?? false);
        if (trim((string)($input['password'] ?? '')) !== '') {
            if (strlen((string)$input['password']) < 8) {
                dashboard_json(['ok' => false, 'error' => 'La password deve contenere almeno 8 caratteri'], 422);
            }
            // The simulator intentionally never persists the submitted secret.
            $state['wifi_key_configured'] = true;
        }
        $state['last_event'] = 'Configurazione Wi-Fi aggiornata';
        $message = 'Configurazione Wi-Fi salvata';
        break;

    case 'save_network':
        $name = dashboard_clean_text($input['router_name'] ?? '', 32);
        $lanIp = dashboard_clean_text($input['lan_ip'] ?? '', 15);
        $start = dashboard_clean_text($input['dhcp_start'] ?? '', 15);
        $end = dashboard_clean_text($input['dhcp_end'] ?? '', 15);
        if ($name === '' || !dashboard_valid_ipv4($lanIp) || !dashboard_valid_ipv4($start) || !dashboard_valid_ipv4($end)) {
            dashboard_json(['ok' => false, 'error' => 'Nome router o indirizzo IPv4 non valido'], 422);
        }
        $state['router_name'] = $name;
        $state['lan_ip'] = $lanIp;
        $state['dhcp_start'] = $start;
        $state['dhcp_end'] = $end;
        $state['dhcp_enabled'] = (bool)($input['dhcp_enabled'] ?? false);
        $state['last_event'] = 'Configurazione LAN aggiornata';
        $message = 'Configurazione di rete salvata';
        break;

    case 'client_access':
        $mac = strtoupper((string)($input['mac'] ?? ''));
        if (!preg_match('/^([0-9A-F]{2}:){5}[0-9A-F]{2}$/', $mac)) {
            dashboard_json(['ok' => false, 'error' => 'Indirizzo MAC non valido'], 422);
        }
        $blocked = array_values(array_unique(array_map('strtoupper', (array)($state['blocked_clients'] ?? []))));
        if ((bool)($input['blocked'] ?? false)) {
            if (!in_array($mac, $blocked, true)) {
                $blocked[] = $mac;
            }
            $message = 'Dispositivo messo in pausa';
        } else {
            $blocked = array_values(array_filter($blocked, static fn(string $item): bool => $item !== $mac));
            $message = 'Accesso dispositivo ripristinato';
        }
        $state['blocked_clients'] = $blocked;
        $state['last_event'] = $message;
        break;

    case 'restart':
        $state['last_event'] = 'Riavvio simulato richiesto';
        $state['restart_requested_at'] = gmdate('c');
        $message = 'Riavvio simulato: nessun comando di sistema è stato eseguito';
        break;

    default:
        dashboard_json(['ok' => false, 'error' => 'Azione sconosciuta'], 400);
}

if (!dashboard_save($state)) {
    dashboard_json(['ok' => false, 'error' => 'Impossibile salvare le impostazioni'], 500);
}

dashboard_json([
    'ok' => true,
    'message' => $message,
    'state' => $state,
    'clients' => dashboard_clients($state),
]);
