// 看门狗模块前端逻辑

function loadConfig() {
    fetch('/api/watchdog/config')
        .then(function (r) { return r.json(); })
        .then(function (cfg) {
            document.getElementById('cfg_enabled').checked = !!cfg.enabled;
            document.getElementById('cfg_check_interval').value = cfg.check_interval;
            document.getElementById('cfg_auto_restart').checked = !!cfg.auto_restart;
            document.getElementById('cfg_max_restarts').value = cfg.max_restarts;
            document.getElementById('cfg_restart_cooldown').value = cfg.restart_cooldown;
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
            var html = '';
            html += '<div><strong>监控运行：</strong>' + mon + '</div>';
            html += '<div><strong>启用状态：</strong>' + enabled + '</div>';
            html += '<div><strong>健康状态：</strong>' + healthy + '</div>';
            html += '<div><strong>上次检查：</strong>' + (s.last_check || '—') + '</div>';
            html += '<div><strong>重启次数：</strong>' + s.restarts_count + '</div>';
            html += '<div><strong>上次重启：</strong>' + (s.last_restart || '—') + '</div>';
            html += '<div><strong>最近事件：</strong>' + (s.last_event || '—') + '</div>';
            document.getElementById('statusArea').innerHTML = html;
        })
        .catch(function () { /* 短暂网络抖动忽略，下一次轮询刷新 */ });
}

function saveConfig() {
    var payload = {
        enabled: document.getElementById('cfg_enabled').checked,
        check_interval: parseInt(document.getElementById('cfg_check_interval').value, 10),
        auto_restart: document.getElementById('cfg_auto_restart').checked,
        max_restarts: parseInt(document.getElementById('cfg_max_restarts').value, 10),
        restart_cooldown: parseInt(document.getElementById('cfg_restart_cooldown').value, 10)
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

function enableWatchdog() {
    fetch('/api/watchdog/enable', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.success) { showToast('看门狗已启用', 'success'); loadConfig(); }
            else { showToast('启用失败', 'error'); }
        })
        .catch(function () { showToast('请求失败', 'error'); });
}

function disableWatchdog() {
    fetch('/api/watchdog/disable', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.success) { showToast('看门狗已禁用', 'success'); loadConfig(); }
            else { showToast('禁用失败', 'error'); }
        })
        .catch(function () { showToast('请求失败', 'error'); });
}

loadConfig();
loadStatus();
setInterval(loadStatus, 3000);
