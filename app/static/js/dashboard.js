/* 状态仪表盘前端逻辑：从 /api/dashboard 拉取聚合数据并填充 #dashStats 卡片。
 * 注意：本文件中的 loadDashboardStats() 专用于填充首页的 #dashStats 状态卡片区，
 * 与 index.html 内联的 loadDashboard()（系统概览）互不干扰、各自轮询。
 */

function loadDashboardStats() {
    fetch('/api/dashboard')
        .then(function (r) { return r.json(); })
        .then(function (d) {
            var sys = (d && d.system) || {};
            var td = (d && d.tooldelta) || {};
            var panel = (d && d.panel) || {};

            // CPU 使用率
            setDashText('dashCpu', fmtPercent(sys.cpu_percent));

            // 内存使用（已用 / 总量，含百分比）
            setDashText(
                'dashMem',
                fmtMB(sys.mem_used_mb) + ' / ' + fmtMB(sys.mem_total_mb) +
                ' (' + fmtPercent(sys.mem_percent) + ')'
            );

            // 磁盘剩余（剩余空间，含已用百分比）
            setDashText(
                'dashDisk',
                fmtGB(sys.disk_free_gb) + ' 剩余 (' + fmtPercent(sys.disk_percent) + ')'
            );

            // ToolDelta 运行状态
            var running = !!(td && td.running);
            setDashText('dashToolStatus', running ? '运行中' : '已停止');
            var toolIcon = document.getElementById('dashToolIcon');
            if (toolIcon) {
                toolIcon.textContent = running ? 'ON' : 'OFF';
            }

            // 看门狗开关
            setDashText('dashWatchdog', panel.watchdog_enabled ? '开' : '关');

            // 服务器连接数
            setDashText('dashConnections', panel.connections_count != null ? panel.connections_count : 0);

            // 定时任务数
            setDashText('dashSchedJobs', panel.scheduler_jobs_count != null ? panel.scheduler_jobs_count : 0);
        })
        .catch(function (e) {
            console.error('loadDashboardStats error', e);
            if (typeof showToast === 'function') {
                showToast('加载仪表盘数据失败', 'error');
            }
        });
}

/* ─── 辅助函数 ───────────────────────────────── */

function setDashText(id, value) {
    var el = document.getElementById(id);
    if (el && value !== undefined && value !== null) {
        el.textContent = String(value);
    }
}

function fmtPercent(v) {
    if (v === undefined || v === null || isNaN(v)) return '0.0%';
    return Number(v).toFixed(1) + '%';
}

function fmtMB(mb) {
    if (mb === undefined || mb === null || isNaN(mb)) return '0 MB';
    if (mb >= 1024) return (mb / 1024).toFixed(1) + ' GB';
    return mb + ' MB';
}

function fmtGB(gb) {
    if (gb === undefined || gb === null || isNaN(gb)) return '0.0 GB';
    return Number(gb).toFixed(2) + ' GB';
}

// 首次调用 + 每 5 秒轮询
loadDashboardStats();
setInterval(loadDashboardStats, 5000);
