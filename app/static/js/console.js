// 控制台交互：命令发送 + 历史回溯(↑/↓) + Tab 自动补全(基于命令库) + 收藏快捷发送
var socket = io({ transports: ['polling'] });
var body = document.getElementById('consoleBody');
var input = document.getElementById('consoleInput');
var statusEl = document.getElementById('consoleStatus');

var HISTORY_KEY = 'td_console_history';
var history = loadHistory();
var histIdx = -1;          // -1 表示正在输入新命令
var cmdLibrary = [];      // 来自 /api/commands 的所有命令 trigger，用于补全

function loadHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
    catch (e) { return []; }
}
function saveHistory(cmd) {
    if (!cmd) return;
    history = history.filter(function (c) { return c !== cmd; });
    history.push(cmd);
    if (history.length > 200) history = history.slice(-200);
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(history)); } catch (e) {}
}

function appendLine(html) {
    if (!body) return;
    // XSS 防护：先用正则过滤脚本、事件处理器、data URI 等明显危险内容
    var safe = (html || '')
        .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
        .replace(/<img[^>]*onerror\s*=[^>]*>/gi, '')
        .replace(/<svg[^>]*onload\s*=[^>]*>/gi, '')
        .replace(/<[^>]*\bon[a-z]+\s*=\s*[^>]*/gi, function(m){return m.replace(/on\w+\s*=\s*/gi,'data-removed=');})
        .replace(/javascript\s*:/gi, 'blocked:')
        .replace(/data\s*:\s*[^;\s"']*/gi, 'blocked:');
    var atBottom = body.scrollHeight - body.scrollTop - body.clientHeight < 50;
    var div = document.createElement('div');
    div.innerHTML = safe;
    // 二次清理：只允许 span 标签，移除任何 script/iframe/object 等可疑节点
    var tags = div.querySelectorAll('*');
    for (var i = 0; i < tags.length; i++) {
        var tag = tags[i];
        if (tag.tagName.toLowerCase() !== 'span') {
            // 非 span 标签：保留其文本内容，但剥离标签本身
            var parent = tag.parentNode;
            while (tag.firstChild) {
                parent.insertBefore(tag.firstChild, tag);
            }
            parent.removeChild(tag);
        }
    }
    body.appendChild(div);
    // 行数上限：保留最近 1000 行
    while (body.children.length > 1000) {
        body.removeChild(body.firstChild);
    }
    if (atBottom) body.scrollTop = body.scrollHeight;
}

var _sendingCmd = false;

function sendCommand(cmd) {
    cmd = (cmd || '').trim();
    if (!cmd) return;
    // 防连点/连发：命令发送间隔过短时忽略（P2-7）
    if (_sendingCmd) return;
    _sendingCmd = true;
    setTimeout(function () { _sendingCmd = false; }, 120);
    appendLine('<span class="c-cmd">$ ' + escapeHtml(cmd) + '</span>');
    socket.emit('console_command', cmd);
    saveHistory(cmd);
}

function moveCursorEnd(el) { setTimeout(function () { el.selectionStart = el.selectionEnd = el.value.length; }, 0); }

// Tab 自动补全：先匹配命令库 trigger，再退而求其次匹配历史命令
function complete() {
    var val = input.value;
    if (!val) return;
    var parts = val.split(/\s+/);
    var prefix = parts[parts.length - 1];
    if (!prefix) return;
    var cands = [];
    cmdLibrary.forEach(function (t) {
        if (t && t.indexOf(prefix) === 0 && cands.indexOf(t) === -1) cands.push(t);
    });
    if (cands.length === 0) {
        history.forEach(function (t) {
            if (t && t.indexOf(prefix) === 0 && cands.indexOf(t) === -1) cands.push(t);
        });
    }
    if (cands.length === 0) return;
    if (cands.length === 1) {
        parts[parts.length - 1] = cands[0];
        input.value = parts.join(' ');
    } else {
        var common = cands[0];
        for (var i = 1; i < cands.length; i++) {
            while (cands[i].indexOf(common) !== 0 && common.length) common = common.slice(0, -1);
        }
        if (common.length > prefix.length) {
            parts[parts.length - 1] = common;
            input.value = parts.join(' ');
        } else {
            appendLine('<span style="color:#aaa;">候选 (' + cands.length + '): ' +
                cands.slice(0, 14).join('  ') + (cands.length > 14 ? ' …' : '') + '</span>');
        }
    }
    moveCursorEnd(input);
}

if (body) body.innerHTML = '<div class="c-loading">正在加载输出...</div>';

if (body) {
    fetch('/api/tool/output?tail=200&html=1')
        .then(function (r) { return r.json(); })
        .then(function (d) {
            body.innerHTML = '';
            if (d.lines && d.lines.length) d.lines.forEach(appendLine);
        })
        .catch(function () { body.innerHTML = '<div class="c-err">获取历史输出失败</div>'; });
}

// 拉取统一命令库用于 Tab 补全（静态扫描 + 运行时注册）
fetch('/api/commands')
    .then(function (r) { return r.json(); })
    .then(function (d) {
        var arr = Array.isArray(d) ? d : (d.plugins || []);
        var lib = [];
        arr.forEach(function (p) {
            (p.commands || []).forEach(function (c) {
                (c.triggers || []).forEach(function (t) {
                    if (t && lib.indexOf(t) === -1) lib.push(t);
                });
            });
        });
        cmdLibrary = lib;
    })
    .catch(function () { cmdLibrary = []; });

socket.on('connect', function () { if (statusEl) statusEl.textContent = '已连接'; });
socket.on('disconnect', function () { if (statusEl) statusEl.textContent = '已断开'; });
socket.on('console_output', function (data) { appendLine(data.data_html || data.data || ''); });

if (input) {
    input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            var cmd = input.value;
            input.value = '';
            histIdx = -1;
            sendCommand(cmd);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (!history.length) return;
            if (histIdx === -1) histIdx = history.length - 1;
            else if (histIdx > 0) histIdx--;
            input.value = history[histIdx];
            moveCursorEnd(input);
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (histIdx === -1) return;
            if (histIdx < history.length - 1) { histIdx++; input.value = history[histIdx]; }
            else { histIdx = -1; input.value = ''; }
            moveCursorEnd(input);
        } else if (e.key === 'Tab') {
            e.preventDefault();
            complete();
        }
    });
    input.focus();
}

function escapeHtml(s) {
    return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
// 渲染收藏的命令为快捷发送 chips（点击即发送到控制台）
function renderFavs() {
    var el = document.getElementById('favStrip');
    if (!el) return;
    fetch('/api/favorites')
        .then(function (r) { return r.json(); })
        .then(function (d) {
            var cmds = d.commands || [];
            if (!cmds.length) {
                el.innerHTML = '<span class="fav-empty">暂无收藏命令 · 在「命令参考」页点 ★ 即可收藏，这里一键发送</span>';
                return;
            }
            el.innerHTML = cmds.map(function (c) {
                return '<button class="fav-chip" onclick=\'sendCommand(' + JSON.stringify(c) + ')\'>' + escapeHtml(c) + '</button>';
            }).join('');
        })
        .catch(function () { el.innerHTML = ''; });
}

function clearConsole() { if (body) body.innerHTML = ''; }

renderFavs();
