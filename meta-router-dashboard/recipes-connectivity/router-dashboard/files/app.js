(() => {
    'use strict';

    const initial = JSON.parse(document.getElementById('bootstrap').textContent || '{}');
    const token = document.querySelector('meta[name="dashboard-token"]').content;
    let state = initial.state || {};
    let clients = initial.clients || [];

    const $ = (selector, root = document) => root.querySelector(selector);
    const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
    const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
    }[char]));

    function duration(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return days ? `${days}g ${hours}h` : `${hours}h ${minutes}m`;
    }

    function updateMetrics(metrics) {
        const cpu = Math.min(100, Number(metrics.cpu_percent || 0));
        const memory = Math.min(100, Number(metrics.memory_percent || 0));
        $('#cpu-value').textContent = `${cpu.toFixed(0)}%`;
        $('#memory-value').textContent = `${memory.toFixed(0)}%`;
        $('#cpu-bar').style.width = `${cpu}%`;
        $('#memory-bar').style.width = `${memory}%`;
        $('#uptime').textContent = duration(Number(metrics.uptime_seconds || 0));
        $('#hostname').textContent = metrics.hostname || 'router';
        $('#kernel-value').textContent = metrics.kernel || '—';
        $('#architecture-value').textContent = metrics.architecture || '—';
        $('#php-value').textContent = metrics.php_version || '—';
        $('#interface-count').textContent = String((metrics.interfaces || []).length);
    }

    function updateState() {
        $$('[data-field="ssid"]').forEach((node) => { node.textContent = state.ssid; });
        $$('[data-field="channel"]').forEach((node) => { node.textContent = state.channel; });
        document.title = `${state.router_name || 'Router'} · Router`;
    }

    function renderClients() {
        $('#client-count').textContent = String(clients.length);
        $('#device-list').innerHTML = clients.map((client) => `
            <div class="device">
                <div><strong>${escapeHtml(client.name)}</strong><small>${escapeHtml(client.ip)} · ${escapeHtml(client.mac)}</small></div>
                <span>${escapeHtml(client.band)}</span>
                <button class="small-button ${client.blocked ? 'blocked' : ''}" data-mac="${escapeHtml(client.mac)}" data-blocked="${client.blocked ? 'false' : 'true'}">${client.blocked ? 'Riattiva' : 'Pausa'}</button>
            </div>
        `).join('');
        $$('.small-button', $('#device-list')).forEach((button) => {
            button.addEventListener('click', () => changeClient(button));
        });
    }

    function toast(message, error = false) {
        const node = $('#toast');
        node.textContent = message;
        node.classList.toggle('error', error);
        node.classList.add('visible');
        clearTimeout(toast.timer);
        toast.timer = setTimeout(() => node.classList.remove('visible'), 3000);
    }

    async function post(payload) {
        const response = await fetch('/api.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Dashboard-Token': token },
            body: JSON.stringify(payload),
        });
        const result = await response.json().catch(() => ({ ok: false, error: 'Risposta non valida' }));
        if (!response.ok || !result.ok) throw new Error(result.error || `Errore ${response.status}`);
        return result;
    }

    async function changeClient(button) {
        button.disabled = true;
        try {
            const result = await post({ action: 'client_access', mac: button.dataset.mac, blocked: button.dataset.blocked === 'true' });
            state = result.state;
            clients = result.clients;
            renderClients();
            toast(result.message);
        } catch (error) {
            button.disabled = false;
            toast(error.message, true);
        }
    }

    async function submit(form, payload) {
        const button = $('button[type="submit"]', form);
        button.disabled = true;
        try {
            const result = await post(payload);
            state = result.state;
            clients = result.clients || clients;
            updateState();
            renderClients();
            if (form.elements.password) form.elements.password.value = '';
            toast(result.message);
        } catch (error) {
            toast(error.message, true);
        } finally {
            button.disabled = false;
        }
    }

    $('#wifi-form').addEventListener('submit', (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        submit(form, {
            action: 'save_wifi',
            ssid: form.elements.ssid.value,
            channel: Number(form.elements.channel.value),
            security: form.elements.security.value,
            password: form.elements.password.value,
            guest_ssid: form.elements.guest_ssid.value,
            wifi_enabled: form.elements.wifi_enabled.checked,
            guest_enabled: form.elements.guest_enabled.checked,
        });
    });

    $('#network-form').addEventListener('submit', (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        submit(form, {
            action: 'save_network',
            router_name: form.elements.router_name.value,
            lan_ip: form.elements.lan_ip.value,
            dhcp_start: form.elements.dhcp_start.value,
            dhcp_end: form.elements.dhcp_end.value,
            dhcp_enabled: form.elements.dhcp_enabled.checked,
        });
    });

    async function refresh(showMessage = false) {
        const button = $('#refresh-button');
        button.disabled = true;
        try {
            const response = await fetch('/api.php', { cache: 'no-store' });
            const result = await response.json();
            if (!response.ok || !result.ok) throw new Error('Aggiornamento fallito');
            state = result.state;
            clients = result.clients;
            updateMetrics(result.metrics);
            updateState();
            renderClients();
            if (showMessage) toast('Dati aggiornati');
        } catch (error) {
            if (showMessage) toast(error.message, true);
        } finally {
            button.disabled = false;
        }
    }

    $('#refresh-button').addEventListener('click', () => refresh(true));
    $('#restart-button').addEventListener('click', async () => {
        try {
            const result = await post({ action: 'restart' });
            state = result.state;
            toast(result.message);
        } catch (error) {
            toast(error.message, true);
        }
    });

    updateMetrics(initial.metrics || {});
    updateState();
    renderClients();
    setInterval(refresh, 10000);
})();
