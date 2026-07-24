// 定时任务模块前端逻辑

function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function typeText(job) {
    if (job.type === 'interval') {
        return '每 ' + (job.interval || '?') + ' 秒';
    }
    if (job.type === 'daily') {
        var hh = String(job.hour === null || job.hour === undefined ? '--' : job.hour).padStart(2, '0');
        var mm = String(job.minute === null || job.minute === undefined ? '--' : job.minute).padStart(2, '0');
        return '每日 ' + hh + ':' + mm;
    }
    return job.type || '';
}

function loadJobs() {
    fetch('/api/scheduler/jobs')
        .then(function (r) { return r.json(); })
        .then(function (jobs) {
            var body = document.getElementById('jobsBody');
            if (!jobs || jobs.length === 0) {
                body.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--ink-subtle)">暂无任务，点击右上角“添加任务”创建。</td></tr>';
                return;
            }
            var html = '';
            jobs.forEach(function (job) {
                var enabled = !!job.enabled;
                // 转义 job.id 防止 onclick 属性上下文注入（单引号闭合）
                var eid = escapeHtml(job.id);
                html += '<tr>';
                html += '<td>' + escapeHtml(job.name) + '</td>';
                html += '<td>' + escapeHtml(typeText(job)) + '</td>';
                html += '<td><code style="font-size:12px">' + escapeHtml(job.command) + '</code></td>';
                html += '<td><label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:12px">'
                    + '<input type="checkbox" ' + (enabled ? 'checked' : '') + ' style="accent-color:var(--primary)" '
                    + 'onchange="toggleEnabled(\'' + eid + '\', this.checked)"> '
                    + (enabled ? '已启用' : '已关闭') + '</label></td>';
                html += '<td>' + escapeHtml(job.run_count || 0) + '</td>';
                html += '<td style="font-size:12px;color:var(--ink-subtle)">' + escapeHtml(job.last_run || '—') + '</td>';
                html += '<td><div style="display:flex;gap:6px;flex-wrap:wrap">'
                    + '<button class="btn btn-outline btn-sm" onclick="openEdit(\'' + eid + '\')">编辑</button>'
                    + '<button class="btn btn-outline btn-sm" onclick="runNow(\'' + eid + '\')">立即运行</button>'
                    + '<button class="btn btn-danger btn-sm" onclick="removeJob(\'' + eid + '\')">删除</button>'
                    + '</div></td>';
                html += '</tr>';
            });
            body.innerHTML = html;
        })
        .catch(function () { showToast('加载任务失败', 'error'); });
}

function toggleEnabled(id, checked) {
    fetch('/api/scheduler/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id, enabled: checked })
    })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.success) { showToast(checked ? '已启用' : '已关闭', 'success'); loadJobs(); }
            else { showToast(d.message || '操作失败', 'error'); loadJobs(); }
        })
        .catch(function () { showToast('请求失败', 'error'); loadJobs(); });
}

function runNow(id) {
    fetch('/api/scheduler/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id })
    })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.success) { showToast('已立即执行', 'success'); loadJobs(); }
            else { showToast(d.message || '执行失败', 'error'); }
        })
        .catch(function () { showToast('请求失败', 'error'); });
}

function removeJob(id) {
    showConfirm('确定删除该定时任务吗？', function (ok) {
        if (!ok) return;
        fetch('/api/scheduler/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id })
        })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (d.success) { showToast('已删除', 'success'); loadJobs(); }
                else { showToast(d.message || '删除失败', 'error'); }
            })
            .catch(function () { showToast('请求失败', 'error'); });
    }, true);
}

// ─── 表单 ───────────────────────────────────────────

function syncTypeFields() {
    var type = document.getElementById('job_type').value;
    var isInterval = type === 'interval';
    document.getElementById('row_interval').style.display = isInterval ? 'block' : 'none';
    document.getElementById('row_daily').style.display = isInterval ? 'none' : 'block';
}

function openAdd() {
    document.getElementById('jobModalTitle').textContent = '添加任务';
    document.getElementById('jobSaveBtn').textContent = '添加';
    document.getElementById('job_id').value = '';
    document.getElementById('job_name').value = '';
    document.getElementById('job_type').value = 'interval';
    document.getElementById('job_interval').value = '3600';
    document.getElementById('job_hour').value = '4';
    document.getElementById('job_minute').value = '0';
    document.getElementById('job_command').value = '';
    document.getElementById('job_enabled').checked = false;
    syncTypeFields();
    document.getElementById('jobModal').classList.add('active');
}

function openEdit(id) {
    fetch('/api/scheduler/jobs')
        .then(function (r) { return r.json(); })
        .then(function (jobs) {
            var job = jobs.find(function (j) { return j.id === id; });
            if (!job) { showToast('任务不存在', 'error'); return; }
            document.getElementById('jobModalTitle').textContent = '编辑任务';
            document.getElementById('jobSaveBtn').textContent = '保存';
            document.getElementById('job_id').value = job.id;
            document.getElementById('job_name').value = job.name || '';
            document.getElementById('job_type').value = job.type || 'interval';
            document.getElementById('job_interval').value = job.interval || 3600;
            document.getElementById('job_hour').value = job.hour === null || job.hour === undefined ? 4 : job.hour;
            document.getElementById('job_minute').value = job.minute === null || job.minute === undefined ? 0 : job.minute;
            document.getElementById('job_command').value = job.command || '';
            document.getElementById('job_enabled').checked = !!job.enabled;
            syncTypeFields();
            document.getElementById('jobModal').classList.add('active');
        })
        .catch(function () { showToast('加载失败', 'error'); });
}

function closeJobModal() {
    closeModal('jobModal');
}

function submitJob() {
    var type = document.getElementById('job_type').value;
    var payload = {
        id: document.getElementById('job_id').value || undefined,
        name: document.getElementById('job_name').value,
        type: type,
        command: document.getElementById('job_command').value,
        enabled: document.getElementById('job_enabled').checked
    };
    // parseInt 失败时回退为 0，避免向服务端发送 NaN
    var safeInt = function (id) { var v = parseInt(document.getElementById(id).value, 10); return isNaN(v) ? 0 : v; };
    if (type === 'interval') {
        payload.interval = safeInt('job_interval');
    } else {
        payload.hour = safeInt('job_hour');
        payload.minute = safeInt('job_minute');
    }

    var isEdit = !!payload.id;
    var url = isEdit ? '/api/scheduler/update' : '/api/scheduler/add';

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.success) {
                showToast(isEdit ? '已保存' : '已添加', 'success');
                closeJobModal();
                loadJobs();
            } else {
                showToast(d.message || '保存失败', 'error');
            }
        })
        .catch(function () { showToast('请求失败', 'error'); });
}

// 类型切换实时更新表单字段显隐
var _typeEl = document.getElementById('job_type');
if (_typeEl) _typeEl.addEventListener('change', syncTypeFields);

loadJobs();
if (window.TDPoll) { window.TDPoll.register(loadJobs, 5000); }
else { setInterval(loadJobs, 5000); }
