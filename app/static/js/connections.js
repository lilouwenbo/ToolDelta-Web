// 服务器连接配置前端逻辑

// 连接列表缓存：避免编辑时再次拉取全列表
var _connCache = [];

function loadConnections() {
    fetch('/api/connections')
        .then(function (r) { return r.json(); })
        .then(function (list) {
            _connCache = list || [];
            var tbody = document.getElementById('connTableBody');
            var empty = document.getElementById('connEmpty');
            if (!tbody) return;
            if (!_connCache.length) {
                tbody.innerHTML = '';
                if (empty) empty.style.display = 'block';
                return;
            }
            if (empty) empty.style.display = 'none';
            tbody.innerHTML = _connCache.map(function (c) {
                var addr = (c.host || '') + ':' + (c.port != null ? c.port : '');
                var def = c.is_default
                    ? '<span class="badge-default">默认</span>'
                    : '<span class="badge-normal">—</span>';
                // 转义 c.id 防止 onclick 属性上下文注入（单引号闭合）
                var eid = escapeHtml(c.id || '');
                return '<tr>' +
                    '<td>' + escapeHtml(c.name || '') + '</td>' +
                    '<td>' + escapeHtml(addr) + '</td>' +
                    '<td>' + escapeHtml(c.protocol || '') + '</td>' +
                    '<td>' + def + '</td>' +
                    '<td style="white-space:nowrap">' +
                        '<button class="btn btn-sm btn-primary" onclick="openForm(\'' + eid + '\')">编辑</button> ' +
                        '<button class="btn btn-sm btn-outline" onclick="setDefault(\'' + eid + '\')">设为默认</button> ' +
                        '<button class="btn btn-sm btn-danger" onclick="removeConnection(\'' + eid + '\')">删除</button>' +
                    '</td>' +
                '</tr>';
            }).join('');
        })
        .catch(function () {
            showToast('加载连接失败', 'error');
        });
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (m) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m];
    });
}

function openForm(id) {
    var modal = document.getElementById('connModal');
    var title = document.getElementById('connModalTitle');
    if (id) {
        title.textContent = '编辑连接';
        // 优先使用缓存，避免重复请求
        var conn = _connCache.find(function (x) { return x.id === id; });
        if (conn) {
            _fillConnForm(conn);
            modal.classList.add('active');
            return;
        }
        // 缓存未命中（如页面刷新后直接编辑）：回退到 fetch
        fetch('/api/connections')
            .then(function (r) { return r.json(); })
            .then(function (list) {
                _connCache = list || [];
                conn = _connCache.find(function (x) { return x.id === id; });
                if (!conn) return;
                _fillConnForm(conn);
                modal.classList.add('active');
            })
            .catch(function () { showToast('加载连接信息失败', 'error'); });
        return;
    }
    title.textContent = '添加连接';
    _fillConnForm(null);
    modal.classList.add('active');
}

// 填充表单：conn 为 null 时清空
function _fillConnForm(conn) {
    document.getElementById('connId').value = conn ? (conn.id || '') : '';
    document.getElementById('connName').value = conn ? (conn.name || '') : '';
    document.getElementById('connHost').value = conn ? (conn.host || '') : '';
    document.getElementById('connPort').value = conn ? (conn.port != null ? conn.port : '') : '';
    document.getElementById('connProtocol').value = conn ? (conn.protocol || 'tcp') : 'tcp';
    document.getElementById('connToken').value = conn ? (conn.token || '') : '';
    document.getElementById('connNote').value = conn ? (conn.note || '') : '';
}

function closeForm() {
    closeModal('connModal');
}

function submitForm() {
    var payload = {
        id: document.getElementById('connId').value || undefined,
        name: document.getElementById('connName').value.trim(),
        host: document.getElementById('connHost').value.trim(),
        port: document.getElementById('connPort').value,
        protocol: document.getElementById('connProtocol').value,
        token: document.getElementById('connToken').value,
        note: document.getElementById('connNote').value,
    };
    var isEdit = !!payload.id;
    var url = isEdit ? '/api/connections/update' : '/api/connections/add';
    var body = isEdit ? {
        id: payload.id, name: payload.name, host: payload.host, port: payload.port,
        protocol: payload.protocol, token: payload.token, note: payload.note,
    } : payload;
    var saveBtn = document.querySelector('#connModal .btn-primary');
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = '保存中...'; }
    var f = window.tdFetch || fetch;
    f(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.success) {
                showToast(isEdit ? '已更新' : '已添加', 'success');
                closeForm();
                loadConnections();
            } else {
                showToast(d.error || '失败', 'error');
            }
        })
        .catch(function (e) {
            showToast((e && e.userMessage) || '请求失败', 'error');
        })
        .finally(function () {
            if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '保存'; }
        });
}

function removeConnection(id) {
    showConfirm('确定删除该连接？', function (ok) {
        if (!ok) return;
        fetch('/api/connections/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id }),
        })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (d.success) {
                    showToast('已删除', 'success');
                    loadConnections();
                } else {
                    showToast(d.error || '失败', 'error');
                }
            })
            .catch(function () {
                showToast('请求失败', 'error');
            });
    });
}

function setDefault(id) {
    fetch('/api/connections/default', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id }),
    })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.success) {
                showToast('已设为默认', 'success');
                loadConnections();
            } else {
                showToast(d.error || '失败', 'error');
            }
        })
        .catch(function () {
            showToast('请求失败', 'error');
        });
}

loadConnections();
