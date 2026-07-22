// 日志增强前端：分级 / 搜索 / 过滤 / 导出 / 按来源筛选
// showToast 由 main.js 全局提供。

var allLogLines = [];

function escapeHtml(text) {
    var d = document.createElement("div");
    d.appendChild(document.createTextNode(text));
    return d.innerHTML;
}

// 填充来源下拉框（含「全部来源」）
function loadSources() {
    var dateSel = document.getElementById("logDate");
    var date = dateSel ? dateSel.value : "today";
    var params = (date && date !== "today") ? ("?date=" + encodeURIComponent(date)) : "";
    fetch("/api/logs/sources" + params)
        .then(function (r) { return r.json(); })
        .then(function (sources) {
            var sel = document.getElementById("logSource");
            if (!sel) return;
            var current = sel.value;
            sel.innerHTML = '<option value="">全部来源</option>';
            (sources || []).forEach(function (s) {
                sel.innerHTML += '<option value="' + s + '">' + s + "</option>";
            });
            sel.value = current;
        })
        .catch(function (e) {
            if (typeof showToast === "function") showToast("加载来源失败: " + e, "error");
        });
}

// 加载日志（调用增强 API，按级别/来源/关键字/日期过滤）
function loadLogs() {
    var dateSel = document.getElementById("logDate");
    var date = dateSel ? dateSel.value : "today";
    if (date === "today") date = "";

    var levelEl = document.getElementById("logLevel");
    var sourceEl = document.getElementById("logSource");
    var keywordEl = document.getElementById("logFilter");

    var level = levelEl ? levelEl.value : "";
    var source = sourceEl ? sourceEl.value : "";
    var keyword = keywordEl ? keywordEl.value.trim() : "";

    var params = new URLSearchParams();
    if (date) params.set("date", date);
    if (level) params.set("level", level);
    if (source) params.set("source", source);
    if (keyword) params.set("keyword", keyword);
    params.set("limit", "500");

    fetch("/api/logs/query?" + params.toString())
        .then(function (r) { return r.json(); })
        .then(function (d) {
            allLogLines = d.lines || [];
            var countEl = document.getElementById("logCount");
            if (countEl) countEl.textContent = allLogLines.length + " 行";
            filterLogs();
        })
        .catch(function (e) {
            if (typeof showToast === "function") showToast("加载日志失败: " + e, "error");
        });
}

// 客户端渲染：按级别配色，并叠加关键字高亮过滤
function filterLogs() {
    var keywordEl = document.getElementById("logFilter");
    var q = keywordEl ? keywordEl.value.trim().toLowerCase() : "";

    var lines = allLogLines.filter(function (l) {
        if (!q) return true;
        var hay = ((l.message || "") + " " + (l.source || "") + " " + (l.level || "")).toLowerCase();
        return hay.indexOf(q) !== -1;
    });

    var body = document.getElementById("logBody");
    if (!body) return;
    body.innerHTML = lines.map(function (l) {
        var cls = "line-output";
        if (l.level === "ERROR") cls = "line-err";
        else if (l.level === "WARN") cls = "line-warn";
        else if (l.level === "INFO") cls = "line-system";
        var text = "[" + l.time + "][" + l.level + "][" + l.source + "] " + l.message;
        return '<div class="' + cls + '">' + escapeHtml(text) + "</div>";
    }).join("");
    body.scrollTop = body.scrollHeight;
}

// 刷新：重新拉取日期列表、来源列表与日志
function refreshLogs() {
    loadDates();
    loadSources();
    loadLogs();
}

// 清屏（保留现有功能）
function clearDisplay() {
    var body = document.getElementById("logBody");
    if (body) body.innerHTML = "";
    allLogLines = [];
    var countEl = document.getElementById("logCount");
    if (countEl) countEl.textContent = "0 行";
}

// 导出：基于当前过滤条件下载 logs_export.txt
function doExport() {
    var dateSel = document.getElementById("logDate");
    var date = dateSel ? dateSel.value : "today";
    if (date === "today") date = "";

    var levelEl = document.getElementById("logLevel");
    var sourceEl = document.getElementById("logSource");
    var keywordEl = document.getElementById("logFilter");

    var level = levelEl ? levelEl.value : "";
    var source = sourceEl ? sourceEl.value : "";
    var keyword = keywordEl ? keywordEl.value.trim() : "";

    var params = new URLSearchParams();
    if (date) params.set("date", date);
    if (level) params.set("level", level);
    if (source) params.set("source", source);
    if (keyword) params.set("keyword", keyword);

    var url = "/api/logs/export?" + params.toString();
    window.open(url, "_blank");
    if (typeof showToast === "function") showToast("已导出日志", "success");
}

// 加载可用日期列表（保留现有功能，调用 /api/logs/files）
function loadDates() {
    fetch("/api/logs/files")
        .then(function (r) { return r.json(); })
        .then(function (files) {
            var sel = document.getElementById("logDate");
            if (!sel) return;
            var current = sel.value;
            sel.innerHTML = '<option value="today">今天</option>';
            (files || []).forEach(function (f) {
                var opt = '<option value="' + f.date + '">' + f.date + " (" +
                    (f.size / 1024).toFixed(1) + " KB)</option>";
                sel.innerHTML += opt;
            });
            sel.value = current;
        });
}

// 初始化
loadDates();
loadSources();
loadLogs();
setInterval(loadLogs, 5000);
