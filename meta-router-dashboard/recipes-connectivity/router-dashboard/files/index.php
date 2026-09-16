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
$bootstrap = json_encode(
    ['state' => $state, 'metrics' => $metrics, 'clients' => $clients],
    JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT
);

function e(mixed $value): string
{
    return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
?>
<!doctype html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="dashboard-token" content="<?= e(dashboard_csrf_token()) ?>">
    <title><?= e($state['router_name']) ?> · Router</title>
    <link rel="stylesheet" href="/assets/app.css">
</head>
<body>
<header class="topbar">
    <a class="brand" href="/" aria-label="Dashboard router"><span>R</span><strong>Router</strong></a>
    <div class="online"><i></i> Online</div>
</header>

<main>
    <section class="intro">
        <div>
            <p>Dashboard</p>
            <h1><?= e($state['router_name']) ?></h1>
            <span>Gestione semplificata del router simulato</span>
        </div>
        <button class="button secondary" id="refresh-button">Aggiorna</button>
    </section>

    <section class="stats" aria-label="Stato rete">
        <article><small>Internet</small><strong class="good">Connesso</strong><span>WAN · <?= e($state['wan_ip']) ?></span></article>
        <article><small>Wi-Fi</small><strong data-field="ssid"><?= e($state['ssid']) ?></strong><span>Canale <b data-field="channel"><?= e($state['channel']) ?></b></span></article>
        <article><small>Dispositivi</small><strong id="client-count"><?= count($clients) ?></strong><span>Client configurati</span></article>
        <article><small>Uptime</small><strong id="uptime">—</strong><span id="hostname"><?= e($metrics['hostname']) ?></span></article>
    </section>

    <div class="columns">
        <section class="panel">
            <div class="panel-title"><div><small>Sistema</small><h2>Risorse</h2></div><span>LIVE</span></div>
            <div class="resource">
                <div><label>CPU <b id="cpu-value">0%</b></label><div class="bar"><i id="cpu-bar"></i></div></div>
                <div><label>Memoria <b id="memory-value">0%</b></label><div class="bar"><i id="memory-bar"></i></div></div>
            </div>
            <dl class="details">
                <div><dt>Kernel</dt><dd id="kernel-value"><?= e($metrics['kernel']) ?></dd></div>
                <div><dt>Architettura</dt><dd id="architecture-value"><?= e($metrics['architecture']) ?></dd></div>
                <div><dt>PHP</dt><dd id="php-value"><?= e($metrics['php_version']) ?></dd></div>
                <div><dt>Interfacce</dt><dd id="interface-count"><?= count($metrics['interfaces']) ?></dd></div>
            </dl>
        </section>

        <section class="panel">
            <div class="panel-title"><div><small>Rete locale</small><h2>Dispositivi</h2></div></div>
            <div id="device-list" class="device-list"></div>
        </section>
    </div>

    <section class="panel settings">
        <div class="panel-title"><div><small>Configurazione</small><h2>Impostazioni</h2></div><span>SIMULAZIONE</span></div>

        <details open>
            <summary>Wi-Fi</summary>
            <form id="wifi-form">
                <label>Nome rete<input name="ssid" maxlength="32" required value="<?= e($state['ssid']) ?>"></label>
                <label>Canale<select name="channel"><?php foreach ([36, 40, 44, 48, 149, 153, 157, 161] as $channel): ?><option<?= (int)$state['channel'] === $channel ? ' selected' : '' ?>><?= $channel ?></option><?php endforeach ?></select></label>
                <label>Sicurezza<select name="security"><option<?= $state['security'] === 'WPA3-Personal' ? ' selected' : '' ?>>WPA3-Personal</option><option<?= $state['security'] === 'WPA2-Personal' ? ' selected' : '' ?>>WPA2-Personal</option><option<?= $state['security'] === 'WPA2/WPA3 Mixed' ? ' selected' : '' ?>>WPA2/WPA3 Mixed</option></select></label>
                <label>Nuova password<input name="password" type="password" minlength="8" placeholder="Lascia vuoto per non cambiarla"></label>
                <label>Rete ospiti<input name="guest_ssid" maxlength="32" required value="<?= e($state['guest_ssid']) ?>"></label>
                <label class="check"><input name="wifi_enabled" type="checkbox" <?= $state['wifi_enabled'] ? 'checked' : '' ?>> Wi-Fi attivo</label>
                <label class="check"><input name="guest_enabled" type="checkbox" <?= $state['guest_enabled'] ? 'checked' : '' ?>> Ospiti attivi</label>
                <button class="button primary" type="submit">Salva Wi-Fi</button>
            </form>
        </details>

        <details>
            <summary>Rete LAN</summary>
            <form id="network-form">
                <label>Nome router<input name="router_name" maxlength="32" required value="<?= e($state['router_name']) ?>"></label>
                <label>Indirizzo LAN<input name="lan_ip" required value="<?= e($state['lan_ip']) ?>"></label>
                <label>DHCP da<input name="dhcp_start" required value="<?= e($state['dhcp_start']) ?>"></label>
                <label>DHCP a<input name="dhcp_end" required value="<?= e($state['dhcp_end']) ?>"></label>
                <label class="check"><input name="dhcp_enabled" type="checkbox" <?= $state['dhcp_enabled'] ? 'checked' : '' ?>> DHCP attivo</label>
                <button class="button primary" type="submit">Salva LAN</button>
            </form>
        </details>
    </section>

    <footer>
        <span>Yocto 6.0.3 · qemuarm64</span>
        <button class="link-button" id="restart-button">Simula riavvio</button>
    </footer>
</main>

<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script id="bootstrap" type="application/json"><?= $bootstrap ?></script>
<script src="/assets/app.js" defer></script>
</body>
</html>
