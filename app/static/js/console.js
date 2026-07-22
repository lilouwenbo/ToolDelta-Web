var socket = io({ transports: ['polling'] });
var body = document.getElementById('consoleBody');
var input = document.getElementById('consoleInput');
var statusEl = document.getElementById('consoleStatus');

function appendLine(html) {
    var atBottom = body.scrollHeight - body.scrollTop - body.clientHeight < 50;
    var div = document.createElement('div');
    div.innerHTML = html;
    body.appendChild(div);
    if (atBottom) body.scrollTop = body.scrollHeight;
}

body.innerHTML = '<div style="color:#666;">正在加载输出...</div>';

fetch('/api/tool/output?tail=200&html=1')
    .then(function(r) { return r.json(); })
    .then(function(d) {
        body.innerHTML = '';
        if (d.lines && d.lines.length) {
            d.lines.forEach(function(line) { appendLine(line); });
        }
    })
    .catch(function() { body.innerHTML = '<div style="color:#e74c3c;">获取历史输出失败</div>'; });

socket.on('connect', function() { statusEl.textContent = '已连接'; });
socket.on('disconnect', function() { statusEl.textContent = '已断开'; });
socket.on('console_output', function(data) {
    appendLine(data.data_html || data.data || '');
});

input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        var cmd = input.value.trim();
        input.value = '';
        if (!cmd) return;
        appendLine('<span style="color:#8f8;">$ ' + cmd.replace(/&/g,'&amp;').replace(/</g,'&lt;') + '</span>');
        socket.emit('console_command', cmd);
    }
});

(function() { input.focus(); })();

function clearConsole() { body.innerHTML = ''; }
