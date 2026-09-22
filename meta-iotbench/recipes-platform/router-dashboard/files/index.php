<?php
declare(strict_types=1);

require '/usr/share/router-dashboard/router.php';

header("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header('Referrer-Policy: no-referrer');
header('Cache-Control: no-store');

$state = dashboard_state();
$metrics = dashboard_live_metrics();
$clients = dashboard_clients($state);
$modules = dashboard_modules();
$sim = dashboard_sim();
$device = dashboard_device();
$bootstrap = json_encode(
    ['state' => $state, 'metrics' => $metrics, 'clients' => $clients, 'sim' => $sim],
    JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT
);

function e(mixed $value): string
{
    return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="dashboard-token" content="<?= e(dashboard_csrf_token()) ?>">
    <title><?= e($device['name']) ?> · IoTBench</title>
    <link rel="stylesheet" href="/assets/app.css">
</head>
<body>
<header class="topbar">
    <a class="brand" href="/" aria-label="Router dashboard"><span>R</span><strong>Router</strong></a>
    <div class="online"><i></i> Online</div>
</header>

<main>
    <section class="intro">
        <div>
            <p>Dashboard · <?= e($device['class']) ?></p>
            <h1><?= e($device['name']) ?></h1>
            <span>Simplified management of the simulated device</span>
        </div>
        <button class="button secondary" id="refresh-button">Refresh</button>
    </section>

    <section class="stats" aria-label="Network status">
        <article><small>Internet</small><strong class="good">Connected</strong><span>WAN · <?= e($state['wan_ip']) ?></span></article>
        <article><small>Wi-Fi</small><strong data-field="ssid"><?= e($state['ssid']) ?></strong><span>Channel <b data-field="channel"><?= e($state['channel']) ?></b></span></article>
        <article><small>Devices</small><strong id="client-count"><?= count($clients) ?></strong><span>Configured clients</span></article>
        <article><small>Uptime</small><strong id="uptime">—</strong><span id="hostname"><?= e($metrics['hostname']) ?></span></article>
    </section>

    <div class="columns">
        <section class="panel">
            <div class="panel-title"><div><small>System</small><h2>Resources</h2></div><span>LIVE</span></div>
            <div class="resource">
                <div><label>CPU <b id="cpu-value">0%</b></label><div class="bar"><i id="cpu-bar"></i></div></div>
                <div><label>Memory <b id="memory-value">0%</b></label><div class="bar"><i id="memory-bar"></i></div></div>
            </div>
            <dl class="details">
                <div><dt>Kernel</dt><dd id="kernel-value"><?= e($metrics['kernel']) ?></dd></div>
                <div><dt>Architecture</dt><dd id="architecture-value"><?= e($metrics['architecture']) ?></dd></div>
                <div><dt>PHP</dt><dd id="php-value"><?= e($metrics['php_version']) ?></dd></div>
                <div><dt>Interfaces</dt><dd id="interface-count"><?= count($metrics['interfaces']) ?></dd></div>
            </dl>
        </section>

        <section class="panel">
            <div class="panel-title"><div><small>Local network</small><h2>Devices</h2></div></div>
            <div id="device-list" class="device-list"></div>
        </section>
    </div>

<?php if ($sim): ?>
    <section class="panel">
        <div class="panel-title"><div><small>Peripherals</small><h2>Sensors</h2></div><span>LIVE</span></div>
        <div id="sensor-list" class="sensor-list"></div>
    </section>
<?php endif ?>

<?php foreach ($modules as $module): ?>
    <section class="panel module-panel">
        <div class="panel-title"><div><small><?= e($module['tag'] ?? 'MODULE') ?></small><h2><?= e($module['title'] ?? $module['id']) ?></h2></div><span>MODULE</span></div>
        <?= is_callable($module['render'] ?? null) ? $module['render']() : '' ?>
    </section>
<?php endforeach ?>

    <section class="panel settings">
        <div class="panel-title"><div><small>Configuration</small><h2>Settings</h2></div><span>SIMULATION</span></div>

        <details open>
            <summary>Wi-Fi</summary>
            <form id="wifi-form">
                <label>Network name<input name="ssid" maxlength="32" required value="<?= e($state['ssid']) ?>"></label>
                <label>Channel<select name="channel"><?php foreach ([36, 40, 44, 48, 149, 153, 157, 161] as $channel): ?><option<?= (int)$state['channel'] === $channel ? ' selected' : '' ?>><?= $channel ?></option><?php endforeach ?></select></label>
                <label>Security<select name="security"><option<?= $state['security'] === 'WPA3-Personal' ? ' selected' : '' ?>>WPA3-Personal</option><option<?= $state['security'] === 'WPA2-Personal' ? ' selected' : '' ?>>WPA2-Personal</option><option<?= $state['security'] === 'WPA2/WPA3 Mixed' ? ' selected' : '' ?>>WPA2/WPA3 Mixed</option></select></label>
                <label>New password<input name="password" type="password" minlength="8" placeholder="Leave blank to keep it"></label>
                <label>Guest network<input name="guest_ssid" maxlength="32" required value="<?= e($state['guest_ssid']) ?>"></label>
                <label class="check"><input name="wifi_enabled" type="checkbox" <?= $state['wifi_enabled'] ? 'checked' : '' ?>> Wi-Fi enabled</label>
                <label class="check"><input name="guest_enabled" type="checkbox" <?= $state['guest_enabled'] ? 'checked' : '' ?>> Guests enabled</label>
                <button class="button primary" type="submit">Save Wi-Fi</button>
            </form>
        </details>

        <details>
            <summary>LAN network</summary>
            <form id="network-form">
                <label>Router name<input name="router_name" maxlength="32" required value="<?= e($state['router_name']) ?>"></label>
                <label>LAN address<input name="lan_ip" required value="<?= e($state['lan_ip']) ?>"></label>
                <label>DHCP from<input name="dhcp_start" required value="<?= e($state['dhcp_start']) ?>"></label>
                <label>DHCP to<input name="dhcp_end" required value="<?= e($state['dhcp_end']) ?>"></label>
                <label class="check"><input name="dhcp_enabled" type="checkbox" <?= $state['dhcp_enabled'] ? 'checked' : '' ?>> DHCP enabled</label>
                <button class="button primary" type="submit">Save LAN</button>
            </form>
        </details>
    </section>

    <footer>
        <span>Yocto 6.0.3 · qemuarm64</span>
        <button class="link-button" id="restart-button">Simulate restart</button>
    </footer>
</main>

<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script id="bootstrap" type="application/json"><?= $bootstrap ?></script>
<script src="/assets/app.js" defer></script>
</body>
</html>
