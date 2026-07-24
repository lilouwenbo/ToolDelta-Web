// 服务器连接配置前端逻辑

function loadConnections() {
    fetch('/api/connections')
        .then(function (r) { return r.json(); })
        .then(function (list) {
            var tbody = document.getElementById('connTableBody');
            var empty = document.getElementById('connEmpty');
            if (!list || list.length === 0) {
                tbody.innerHTML = '';
                empty.style.display = 'block';
                return;
            }
            empty.style.display = 'none';
            tbody.innerHTML = list.map(function (c) {
                var addr = (c.host || '') + ':' + (c.port != null ? c.port : '');
                var def = c.is_default
                    ? '<span class="badge-default">默认</span>'
                    : '<span class="badge-normal">—</span>';
                return '<tr>' +
                    '<td>' + escapeHtml(c.name || '') + '</td>' +
                    '<td>' + escapeHtml(addr) + '</td>' +
                    '<td>' + escapeHtml(c.protocol || '') + '</td>' +
                    '<td>' + def + '</td>' +
                    '<td style="white-space:nowrap">' +
                        '<button class="btn btn-sm btn-primary" onclick="openForm(\'' + c.id + '\')">编辑</button> ' +
                        '<button class="btn btn-sm btn-outline" onclick="setDefault(\'' + c.id + '\')">设为默认</button> ' +
                        '<button class="btn btn-sm btn-danger" onclick="removeConnection(\'' + c.id + '\')">删除</button>' +
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
        var conn = null;
        // 先从已加载列表匹配
        fetch('/api/connections')
            .then(function (r) { return r.json(); })
            .then(function (list) {
                conn = (list || []).find(function (x) { return x.id === id; });
                if (!conn) return;
                document.getElementById('connId').value = conn.id;
                document.getElementById('connName').value = conn.name || '';
                document.getElementById('connHost').value = conn.host || '';
                document.getElementById('connPort').value = conn.port != null ? conn.port : '';
                document.getElementById('connProtocol').value = conn.protocol || 'tcp';
                document.getElementById('connToken').value = conn.token || '';
                document.getElementById('connNote').value = conn.note || '';
                modal.classList.add('active');
            });
        return;
    }
    title.textContent = '添加连接';
    document.getElementById('connId').value = '';
    document.getElementById('connName').value = '';
    document.getElementById('connHost').value = '';
    document.getElementById('connPort').value = '';
    document.getElementById('connProtocol').value = 'tcp';
    document.getElementById('connToken').value = '';
    document.getElementById('connNote').value = '';
    modal.classList.add('active');
}

function closeForm() {
    document.getElementById('connModal').classList.remove('active');
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
    if (isEdit) {
        // 编辑时仅提交有变化的字段语义：保留 id，其余照旧提交
        var body = {
            id: payload.id,
            name: payload.name,
            host: payload.host,
            port: payload.port,
            protocol: payload.protocol,
            token: payload.token,
            note: payload.note,
        };
    } else {
        var body = payload;
    }
    fetch(url, {
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
        .catch(function () {
            showToast('请求失败', 'error');
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
