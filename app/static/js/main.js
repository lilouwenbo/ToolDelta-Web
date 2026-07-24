// ─── Toast 通知系统（升级版：进度条 / 点击关闭 / 堆叠上限 / 分类型时长） ───
var _TOAST_MAX = 5;            // 最多同时显示 5 条
var _TOAST_DURATIONS = { success: 3000, info: 3500, error: 6000, warning: 5000 };
function showToast(msg, type) {
    type = type || 'info';
    var container = document.getElementById('toastContainer');
    if (!container) return;
    // 堆叠上限：超出移除最早的一条
    while (container.children.length >= _TOAST_MAX) {
        container.removeChild(container.firstChild);
    }
    var dur = _TOAST_DURATIONS[type] || 3500;
    var t = document.createElement('div');
    t.className = 'toast ' + type;
    t.setAttribute('role', 'status');
    t.innerHTML = '<span class="toast-msg">' + _escHtml(msg) + '</span><button class="toast-close" aria-label="关闭">×</button><span class="toast-bar"></span>';
    // 点击/触摸关闭
    t.addEventListener('click', function() { removeToast(t); });
    container.appendChild(t);
    // 进度条动画
    var bar = t.querySelector('.toast-bar');
    if (bar) {
        // 强制重排后启动宽度过渡
        requestAnimationFrame(function() {
            bar.style.transition = 'width ' + dur + 'ms linear';
            bar.style.width = '0%';
        });
    }
    t._timer = setTimeout(function() { removeToast(t); }, dur);
    // 悬停暂停
    t.addEventListener('mouseenter', function() { if (t._timer) { clearTimeout(t._timer); t._timer = null; } if (bar) { bar.style.transition = 'none'; } });
    t.addEventListener('mouseleave', function() {
        if (bar) { var w = bar.offsetWidth; bar.style.transition = 'width ' + Math.max(500, dur) + 'ms linear'; bar.style.width = '0%'; }
        t._timer = setTimeout(function() { removeToast(t); }, Math.max(1000, dur));
    });
}
function removeToast(t) {
    if (!t || !t.parentNode) return;
    if (t._timer) { clearTimeout(t._timer); t._timer = null; }
    t.classList.add('toast-out');
    setTimeout(function() { if (t.parentNode) t.parentNode.removeChild(t); }, 200);
}
function _escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ─── ToolDelta 启停 ───
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

// ─── 自定义确认弹窗（替代浏览器 confirm） + 输入确认弹窗 ───
var _confirmCallback = null;
var _promptCallback = null;
var _lastFocus = null;  // 打开弹窗前记录焦点，关闭后归还

function showConfirm(msg, callback, danger) {
    _lastFocus = document.activeElement;
    document.getElementById('confirmMessage').textContent = msg;
    var okBtn = document.getElementById('confirmOkBtn');
    okBtn.className = 'btn ' + (danger === false ? 'btn-primary' : 'btn-danger');
    okBtn.textContent = '确定';
    _confirmCallback = callback;
    var modal = document.getElementById('confirmModal');
    modal.classList.add('active');
    setTimeout(function() { okBtn.focus(); }, 50);
}

function closeConfirm(result) {
    document.getElementById('confirmModal').classList.remove('active');
    if (_confirmCallback) {
        _confirmCallback(result);
        _confirmCallback = null;
    }
    if (_lastFocus && _lastFocus.focus) _lastFocus.focus();
}

// 自定义输入弹窗（替代浏览器 prompt）
function showPrompt(title, placeholder, defaultValue, callback) {
    _lastFocus = document.activeElement;
    var modal = document.getElementById('promptModal');
    if (!modal) return;
    document.getElementById('promptTitle').textContent = title;
    var input = document.getElementById('promptInput');
    input.placeholder = placeholder || '';
    input.value = defaultValue || '';
    _promptCallback = callback;
    modal.classList.add('active');
    setTimeout(function() { input.focus(); input.select(); }, 50);
}

function closePrompt(result) {
    var modal = document.getElementById('promptModal');
    if (modal) modal.classList.remove('active');
    var val = result ? document.getElementById('promptInput').value : null;
    if (_promptCallback) {
        _promptCallback(val);
        _promptCallback = null;
    }
    if (_lastFocus && _lastFocus.focus) _lastFocus.focus();
}

// ─── 模态框：Esc 关闭 + 背景点击关闭 + 焦点陷阱 ───
function _openModal(id) {
    _lastFocus = document.activeElement;
    var m = document.getElementById(id);
    if (!m) return;
    m.classList.add('active');
    var focusable = m.querySelectorAll('input,select,textarea,button');
    if (focusable.length) setTimeout(function() { focusable[0].focus(); }, 50);
}
function _closeModal(id) {
    var m = document.getElementById(id);
    if (!m) return;
    m.classList.remove('active');
    if (_lastFocus && _lastFocus.focus) _lastFocus.focus();
}
function closeModal(id) { _closeModal(id); }

// 兼容旧调用：点击 .modal-overlay 背景关闭（点击内容不关闭）
document.addEventListener('click', function(e) {
    if (e.target.classList && e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
        if (_lastFocus && _lastFocus.focus) _lastFocus.focus();
    }
});

// Esc 关闭最顶层弹窗 + 焦点陷阱
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' || e.keyCode === 27) {
        // 找最顶层 active 的 modal-overlay
        var modals = document.querySelectorAll('.modal-overlay.active');
        if (modals.length) {
            var top = modals[modals.length - 1];
            // 确认弹窗走专用回调
            if (top.id === 'confirmModal') { closeConfirm(false); }
            else if (top.id === 'promptModal') { closePrompt(false); }
            else { top.classList.remove('active'); if (_lastFocus && _lastFocus.focus) _lastFocus.focus(); }
            e.preventDefault();
        }
        // 没有弹窗时，移动端关闭侧边栏
        else if (document.body.classList.contains('sidebar-open')) {
            document.body.classList.remove('sidebar-open');
        }
        return;
    }
    // 焦点陷阱：Tab 在弹窗内循环
    if (e.key === 'Tab' || e.keyCode === 9) {
        var active = document.querySelector('.modal-overlay.active');
        if (!active) return;
        var f = active.querySelectorAll('input:not([type=hidden]),select,textarea,button,a[href],[tabindex]:not([tabindex="-1"])');
        if (!f.length) return;
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            last.focus(); e.preventDefault();
        } else if (!e.shiftKey && document.activeElement === last) {
            first.focus(); e.preventDefault();
        }
    }
});

// ─── 全局快捷键：/ 聚焦搜索框（非输入态时） ───
document.addEventListener('keydown', function(e) {
    if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
    var tag = (document.activeElement && document.activeElement.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    var search = document.querySelector('input[type=text][id*=Search], input[type=text][id*=search], #pluginSearch, #searchInput, #presetSearch, #marketSearch, #commandSearch');
    if (search) { search.focus(); e.preventDefault(); }
});

// ─── Tab 切换（含 aria-selected） ───
document.addEventListener('click', function(e) {
    var tabBtn = e.target.closest('.tab-btn');
    if (!tabBtn) return;
    var tabId = tabBtn.getAttribute('data-tab');
    var parent = tabBtn.closest('.modal') || tabBtn.closest('.card') || document;
    parent.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); b.setAttribute('aria-selected', 'false'); });
    tabBtn.classList.add('active');
    tabBtn.setAttribute('aria-selected', 'true');
    parent.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
    var target = document.getElementById(tabId);
    if (target) target.classList.add('active');
});

// ─── 通用：按钮禁用防双击 + 自动恢复 ───
function withGuard(btn, fn) {
    if (!btn) return fn();
    if (btn.disabled) return;
    var orig = btn.textContent;
    btn.disabled = true;
    btn.textContent = '处理中...';
    var p = fn();
    if (p && p.then) {
        p.then(function() { btn.disabled = false; btn.textContent = orig; })
         .catch(function() { btn.disabled = false; btn.textContent = orig; });
    } else {
        btn.disabled = false; btn.textContent = orig;
    }
    return p;
}

// ─── 状态轮询 ───
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
