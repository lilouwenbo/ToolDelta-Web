// Toast notifications
function showToast(msg, type) {
    type = type || 'info';
    var container = document.getElementById('toastContainer');
    var t = document.createElement('div');
    t.className = 'toast ' + type;
    t.textContent = msg;
    container.appendChild(t);
    setTimeout(function() { t.remove(); }, 3000);
}

// ToolDelta toggle start/stop
function toggleTool() {
    var btn = document.getElementById('mainToggleBtn') || document.getElementById('consoleToggleBtn');
    if (!btn) return;
    var isRunning = btn.getAttribute('data-running') === 'true';
    btn.disabled = true;
    btn.textContent = '操作中...';
    var url = isRunning ? '/api/tool/stop' : '/api/tool/start';
    fetch(url, { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.success) {
                showToast(isRunning ? '已停止' : '已启动', 'success');
                updateToggleState(!isRunning);
            } else {
                showToast('操作失败', 'error');
                btn.disabled = false;
                btn.textContent = isRunning ? '停止' : '启动';
            }
        })
        .catch(function() {
            showToast('请求失败', 'error');
            btn.disabled = false;
            btn.textContent = isRunning ? '停止' : '启动';
        });
}

function updateToggleState(running) {
    var btn1 = document.getElementById('mainToggleBtn');
    var btn2 = document.getElementById('consoleToggleBtn');
    [btn1, btn2].forEach(function(btn) {
        if (!btn) return;
        btn.disabled = false;
        btn.setAttribute('data-running', running ? 'true' : 'false');
        btn.textContent = running ? '停止' : '启动';
        btn.className = 'btn ' + (running ? 'btn-danger' : 'btn-success');
    });
    var sd = document.getElementById('sidebarStatus');
    if (sd) {
        sd.className = 'status-dot ' + (running ? 'running' : 'stopped');
        sd.title = running ? '运行中' : '已停止';
    }
}

// Custom confirm dialog (replaces browser confirm())
var _confirmCallback = null;

function showConfirm(msg, callback, danger) {
    document.getElementById('confirmMessage').textContent = msg;
    var okBtn = document.getElementById('confirmOkBtn');
    okBtn.className = 'btn ' + (danger === false ? 'btn-primary' : 'btn-danger');
    okBtn.textContent = '确定';
    _confirmCallback = callback;
    document.getElementById('confirmModal').classList.add('active');
}

function closeConfirm(result) {
    document.getElementById('confirmModal').classList.remove('active');
    if (_confirmCallback) {
        _confirmCallback(result);
        _confirmCallback = null;
    }
}

// Tab switching
document.addEventListener('click', function(e) {
    var tabBtn = e.target.closest('.tab-btn');
    if (!tabBtn) return;
    var tabId = tabBtn.getAttribute('data-tab');
    var parent = tabBtn.closest('.modal') || tabBtn.closest('.card') || document;
    parent.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
    tabBtn.classList.add('active');
    parent.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
    var target = document.getElementById(tabId);
    if (target) target.classList.add('active');
});

// Status polling
function checkStatus() {
    fetch('/api/status')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            updateToggleState(d.running);
        })
        .catch(function() {});
}
setInterval(checkStatus, 3000);
setTimeout(checkStatus, 500);
