// 看门狗模块前端逻辑

// 转义服务端数据，防止注入到 innerHTML
function _esc(s) {
    if (s === null || s === undefined) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function loadConfig() {
    fetch('/api/watchdog/config')
        .then(function (r) { return r.json(); })
        .then(function (cfg) {
            var setVal = function (id, v) { var el = document.getElementById(id); if (el) el.value = v; };
            var setChk = function (id, v) { var el = document.getElementById(id); if (el) el.checked = !!v; };
            setChk('cfg_enabled', cfg.enabled);
            setVal('cfg_check_interval', cfg.check_interval);
            setChk('cfg_auto_restart', cfg.auto_restart);
            setVal('cfg_max_restarts', cfg.max_restarts);
            setVal('cfg_restart_cooldown', cfg.restart_cooldown);
        })
        .catch(function () { showToast('加载配置失败', 'error'); });
}

function loadStatus() {
    fetch('/api/watchdog/status')
        .then(function (r) { return r.json(); })
        .then(function (s) {
            var mon = s.monitor_running ? '运行中' : '已停止';
            var healthy = s.healthy ? '正常' : '异常';
            var enabled = s.enabled ? '已启用' : '未启用';
            // 所有服务端字段经 _esc 转义后再拼入 HTML，防止 XSS
            var html = '';
            html += '<div><strong>监控运行：</strong>' + _esc(mon) + '</div>';
            html += '<div><strong>启用状态：</strong>' + _esc(enabled) + '</div>';
            html += '<div><strong>健康状态：</strong>' + _esc(healthy) + '</div>';
            html += '<div><strong>上次检查：</strong>' + _esc(s.last_check || '—') + '</div>';
            html += '<div><strong>重启次数：</strong>' + _esc(s.restarts_count) + '</div>';
            html += '<div><strong>上次重启：</strong>' + _esc(s.last_restart || '—') + '</div>';
            html += '<div><strong>最近事件：</strong>' + _esc(s.last_event || '—') + '</div>';
            document.getElementById('statusArea').innerHTML = html;
        })
        .catch(function () { /* 短暂网络抖动忽略，下一次轮询刷新 */ });
}

function saveConfig() {
    // parseInt 失败时回退为 0，避免向服务端发送 NaN
    var safeInt = function (id) { var v = parseInt(document.getElementById(id).value, 10); return isNaN(v) ? 0 : v; };
    var payload = {
        enabled: document.getElementById('cfg_enabled').checked,
        check_interval: safeInt('cfg_check_interval'),
        auto_restart: document.getElementById('cfg_auto_restart').checked,
        max_restarts: safeInt('cfg_max_restarts'),
        restart_cooldown: safeInt('cfg_restart_cooldown')
    };
    fetch('/api/watchdog/set', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.success) { showToast('配置已保存', 'success'); }
            else { showToast('配置保存失败（参数不合法）', 'error'); }
        })
        .catch(function () { showToast('请求失败', 'error'); });
}

function enableWatchdog(btn) {
    if (btn) { btn.disabled = true; }
    fetch('/api/watchdog/enable', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.success) { showToast('看门狗已启用', 'success'); loadConfig(); }
            else { showToast('启用失败', 'error'); }
        })
        .catch(function () { showToast('请求失败', 'error'); })
        .finally(function () { if (btn) { btn.disabled = false; } });
}

function disableWatchdog(btn) {
    if (btn) { btn.disabled = true; }
    fetch('/api/watchdog/disable', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.success) { showToast('看门狗已禁用', 'success'); loadConfig(); }
            else { showToast('禁用失败', 'error'); }
        })
        .catch(function () { showToast('请求失败', 'error'); })
        .finally(function () { if (btn) { btn.disabled = false; } });
}

loadConfig();
loadStatus();
if (window.TDPoll) { window.TDPoll.register(loadStatus, 3000); }
else { setInterval(loadStatus, 3000); }
