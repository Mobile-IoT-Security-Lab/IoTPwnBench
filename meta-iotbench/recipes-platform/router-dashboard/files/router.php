<?php
declare(strict_types=1);

// The upstream lighttpd systemd unit forbids writable/executable memory unless a
// vulnerability module relaxes it. Disable PCRE's optional JIT so PHP respects
// that hardening policy when it is in effect.
ini_set('pcre.jit', '0');
ini_set('display_errors', '0');
ini_set('log_errors', '1');

const DASHBOARD_STATE_FILE = '/var/lib/router-dashboard/settings.json';
const DASHBOARD_MODULES_DIR = '/usr/share/router-dashboard/modules';
const DASHBOARD_SIM_FILE = '/run/iotbench/state.json';
const DASHBOARD_DEVICE_FILE = '/etc/iotbench/device.conf';

// Device identity from /etc/iotbench/device.conf (shipped by each device
// profile). Lets the shared web admin show which device class it is running on.
function dashboard_device(): array
{
    $info = ['name' => 'Edge One', 'class' => 'router'];
    foreach (@file(DASHBOARD_DEVICE_FILE) ?: [] as $line) {
        if (preg_match('/^\s*(DEVICE_NAME|DEVICE_CLASS)\s*=\s*"?([^"\r\n]*)"?/', $line, $m)) {
            $info[$m[1] === 'DEVICE_NAME' ? 'name' : 'class'] = trim($m[2]);
        }
    }
    return $info;
}

// Live peripheral values produced by iotbench-simd. Returns a map of
// name => ['value' => ..., 'unit' => ...]; empty if the simulator is not running.
function dashboard_sim(): array
{
    $raw = @file_get_contents(DASHBOARD_SIM_FILE);
    if ($raw === false) {
        return [];
    }
    $data = json_decode($raw, true);
    return is_array($data['peripherals'] ?? null) ? $data['peripherals'] : [];
}

// --- Vulnerability module registry ------------------------------------------
// Each firmware ships zero or more modules under DASHBOARD_MODULES_DIR. A module
// is a <id>/module.php file that calls dashboard_register_module() with a panel
// renderer and named API action handlers. The core dashboard stays identical
// across firmwares; only the installed modules differ.

$GLOBALS['dashboard_modules'] = [];

function dashboard_register_module(array $module): void
{
    if (isset($module['id'])) {
        $GLOBALS['dashboard_modules'][(string)$module['id']] = $module;
    }
}

function dashboard_modules(): array
{
    static $loaded = false;
    if (!$loaded) {
        foreach (glob(DASHBOARD_MODULES_DIR . '/*/module.php') ?: [] as $file) {
            require $file;
        }
        $loaded = true;
    }
    return $GLOBALS['dashboard_modules'];
}

function dashboard_defaults(): array
{
    return [
        'router_name' => 'Edge One',
        'wan_mode' => 'dhcp',
        'wan_ip' => '10.0.2.15',
        'lan_ip' => '192.168.8.1',
        'lan_mask' => '255.255.255.0',
        'dhcp_enabled' => true,
        'dhcp_start' => '192.168.8.100',
        'dhcp_end' => '192.168.8.199',
        'wifi_enabled' => true,
        'ssid' => 'EdgeOne-5G',
        'security' => 'WPA3-Personal',
        'channel' => 44,
        'guest_enabled' => true,
        'guest_ssid' => 'EdgeOne-Guest',
        'wifi_key_configured' => true,
        'blocked_clients' => [],
        'updated_at' => null,
        'last_event' => 'Firmware started',
    ];
}

function dashboard_state(): array
{
    $state = dashboard_defaults();
    $raw = @file_get_contents(DASHBOARD_STATE_FILE);
    if ($raw !== false) {
        $stored = json_decode($raw, true);
        if (is_array($stored)) {
            $state = array_replace($state, $stored);
        }
    }
    return $state;
}

function dashboard_save(array &$state): bool
{
    $state['updated_at'] = gmdate('c');
    $dir = dirname(DASHBOARD_STATE_FILE);
    $tmp = @tempnam($dir, '.settings-');
    if ($tmp === false) {
        return false;
    }
    $json = json_encode($state, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    $saved = $json !== false && @file_put_contents($tmp, $json . "\n", LOCK_EX) !== false;
    if ($saved) {
        @chmod($tmp, 0640);
        $saved = @rename($tmp, DASHBOARD_STATE_FILE);
    }
    if (!$saved) {
        @unlink($tmp);
    }
    return $saved;
}

function dashboard_read_number(string $path): int
{
    $value = @file_get_contents($path);
    return $value === false ? 0 : (int)trim($value);
}

function dashboard_live_metrics(): array
{
    $uptimeRaw = @file_get_contents('/proc/uptime');
    $uptime = $uptimeRaw === false ? 0 : (int)(float)explode(' ', trim($uptimeRaw))[0];

    $loadRaw = @file_get_contents('/proc/loadavg');
    $load = $loadRaw === false ? 0.0 : (float)explode(' ', trim($loadRaw))[0];
    $cores = max(1, count(glob('/sys/devices/system/cpu/cpu[0-9]*') ?: []));
    $cpu = min(100, round(($load / $cores) * 100, 1));

    $memory = ['total' => 0, 'available' => 0];
    foreach (@file('/proc/meminfo') ?: [] as $line) {
        if (preg_match('/^(MemTotal|MemAvailable):\s+(\d+)/', $line, $match)) {
            $memory[$match[1] === 'MemTotal' ? 'total' : 'available'] = (int)$match[2] * 1024;
        }
    }
    $used = max(0, $memory['total'] - $memory['available']);
    $memoryPercent = $memory['total'] > 0 ? round($used / $memory['total'] * 100, 1) : 0;

    $interfaces = [];
    foreach (glob('/sys/class/net/*') ?: [] as $path) {
        $name = basename($path);
        if ($name === 'lo') {
            continue;
        }
        $interfaces[] = [
            'name' => $name,
            'status' => trim((string)@file_get_contents($path . '/operstate')),
            'mac' => trim((string)@file_get_contents($path . '/address')),
            'rx_bytes' => dashboard_read_number($path . '/statistics/rx_bytes'),
            'tx_bytes' => dashboard_read_number($path . '/statistics/tx_bytes'),
        ];
    }

    $temperature = null;
    foreach (glob('/sys/class/thermal/thermal_zone*/temp') ?: [] as $path) {
        $reading = dashboard_read_number($path);
        if ($reading > 0) {
            $temperature = round($reading > 1000 ? $reading / 1000 : $reading, 1);
            break;
        }
    }

    return [
        'hostname' => trim((string)@file_get_contents('/proc/sys/kernel/hostname')) ?: 'router',
        'uptime_seconds' => $uptime,
        'load' => $load,
        'cpu_percent' => $cpu,
        'memory_used' => $used,
        'memory_total' => $memory['total'],
        'memory_percent' => $memoryPercent,
        'temperature' => $temperature,
        'interfaces' => $interfaces,
        'kernel' => php_uname('r'),
        'architecture' => php_uname('m'),
        'php_version' => PHP_VERSION,
        'time' => gmdate('c'),
    ];
}

function dashboard_clients(array $state): array
{
    $clients = [
        ['name' => 'Studio MacBook', 'ip' => '192.168.8.104', 'mac' => '72:8A:21:4E:90:1C', 'type' => 'Laptop', 'band' => '5 GHz', 'signal' => -42, 'traffic' => 18700000],
        ['name' => 'Living Room TV', 'ip' => '192.168.8.118', 'mac' => '30:5A:3A:17:B4:09', 'type' => 'Smart TV', 'band' => 'Ethernet', 'signal' => null, 'traffic' => 92400000],
        ['name' => "Luca's Phone", 'ip' => '192.168.8.121', 'mac' => 'AE:91:0B:8C:2F:77', 'type' => 'Smartphone', 'band' => '5 GHz', 'signal' => -56, 'traffic' => 6800000],
        ['name' => 'Thermostat', 'ip' => '192.168.8.133', 'mac' => '8C:4B:14:22:D1:05', 'type' => 'IoT', 'band' => '2.4 GHz', 'signal' => -68, 'traffic' => 430000],
        ['name' => 'Guest iPad', 'ip' => '192.168.8.151', 'mac' => '5E:11:C8:45:6A:33', 'type' => 'Tablet', 'band' => 'Guest', 'signal' => -61, 'traffic' => 2100000],
    ];
    $blocked = array_map('strtoupper', is_array($state['blocked_clients'] ?? null) ? $state['blocked_clients'] : []);
    foreach ($clients as &$client) {
        $client['blocked'] = in_array(strtoupper($client['mac']), $blocked, true);
    }
    unset($client);
    return $clients;
}

function dashboard_csrf_token(): string
{
    $machineId = trim((string)@file_get_contents('/etc/machine-id'));
    return hash('sha256', $machineId . php_uname('n') . 'router-dashboard-v1');
}

function dashboard_json(array $payload, int $status = 200): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($payload, JSON_UNESCAPED_SLASHES);
    exit;
}

function dashboard_clean_text(mixed $value, int $max): string
{
    $value = trim((string)$value);
    $value = preg_replace('/[\x00-\x1F\x7F]/u', '', $value) ?? '';
    return function_exists('mb_substr') ? mb_substr($value, 0, $max) : substr($value, 0, $max);
}

function dashboard_valid_ipv4(string $ip): bool
{
    if (!preg_match('/^\d{1,3}(\.\d{1,3}){3}$/', $ip)) {
        return false;
    }
    foreach (explode('.', $ip) as $part) {
        if ((int)$part > 255) {
            return false;
        }
    }
    return true;
}
