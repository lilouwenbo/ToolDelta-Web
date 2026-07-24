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

            // CPU 使用率（count-up 动画）
            if (typeof sys.cpu_percent === 'number') {
                animateCount('dashCpu', sys.cpu_percent, '%');
            } else {
                setDashText('dashCpu', fmtPercent(sys.cpu_percent));
            }

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

            // 服务器连接数（count-up 动画）
            if (typeof panel.connections_count === 'number') {
                animateCount('dashConnections', panel.connections_count);
            } else {
                setDashText('dashConnections', panel.connections_count != null ? panel.connections_count : 0);
            }

            // 定时任务数（count-up 动画）
            if (typeof panel.scheduler_jobs_count === 'number') {
                animateCount('dashSchedJobs', panel.scheduler_jobs_count);
            } else {
                setDashText('dashSchedJobs', panel.scheduler_jobs_count != null ? panel.scheduler_jobs_count : 0);
            }
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

// 数字 count-up 动画：从当前值过渡到目标值（300ms）
var _countTimers = {};
function animateCount(id, target, suffix) {
    var el = document.getElementById(id);
    if (!el) return;
    suffix = suffix || '';
    // 解析当前显示值（支持 "75.0%" / "1.2 GB / 8.0 GB (15.0%)" 这种复合文本时跳过动画）
    var cur = parseFloat(el.textContent) || 0;
    if (isNaN(target) || cur === target) { el.textContent = target + suffix; return; }
    // 清理旧定时器（避免元素被复用时多个动画叠加）
    if (_countTimers[id]) { clearInterval(_countTimers[id]); delete _countTimers[id]; }
    var start = cur, delta = target - cur, startTime = Date.now(), dur = 300;
    _countTimers[id] = setInterval(function() {
        // 元素可能已被移除（SPA 场景 / 页面切换），定时器需自清理避免泄漏
        if (!document.getElementById(id)) {
            clearInterval(_countTimers[id]);
            delete _countTimers[id];
            return;
        }
        var t = Math.min(1, (Date.now() - startTime) / dur);
        var eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
        var v = start + delta * eased;
        // 整数 vs 小数
        el.textContent = (Number.isInteger(target) ? Math.round(v) : v.toFixed(1)) + suffix;
        if (t >= 1) { clearInterval(_countTimers[id]); delete _countTimers[id]; }
    }, 16);
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

// 首次调用 + 每 5 秒轮询（统一走 TDPoll：页面隐藏/离线时自动暂停）
// 不再用裸 setInterval 作 fallback，避免 main.js 加载延迟时双重轮询。
loadDashboardStats();
if (window.TDPoll) { window.TDPoll.register(loadDashboardStats, 5000); }
