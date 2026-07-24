// 依赖安装进度 UI：高斯模糊遮罩 + 安装方式选择 + 动画进度条 + 实时日志
(function () {
  var overlay = document.getElementById('depOverlay');
  if (!overlay) return;
  var bar = document.getElementById('depBar');
  var percent = document.getElementById('depPercent');
  var stage = document.getElementById('depStage');
  var mirror = document.getElementById('depMirror');
  var log = document.getElementById('depLog');
  var actions = document.getElementById('depActions');
  var choose = document.getElementById('depChoose');
  var run = document.getElementById('depRun');
  var title = document.getElementById('depTitle');

  function showOverlay() { overlay.classList.add('active'); }
  function hideOverlay() { overlay.classList.remove('active'); }
  function showRun() { choose.style.display = 'none'; run.style.display = 'block'; }
  function showChoose() {
    run.style.display = 'none';
    choose.style.display = 'block';
    actions.style.display = 'none';
  }

  function applyDep(d) {
    if (!d) return;
    var p = Math.max(0, Math.min(100, d.progress || 0));
    bar.style.width = p + '%';
    percent.textContent = p + '%';
    stage.textContent = d.stage || (d.ready ? '依赖已就绪' : '准备中…');
    mirror.textContent = d.mirror || (d.status === 'installing' ? '测速中…' : '—');
    if (d.log_tail && d.log_tail.length) {
      log.textContent = d.log_tail.join('\n');
      log.scrollTop = log.scrollHeight;
    }
    if (d.ready) {
      hideOverlay();
    } else {
      showOverlay();
      showRun();
      actions.style.display = (d.status === 'failed') ? 'flex' : 'none';
    }
  }

  // 返回「选择安装方式」卡片
  window.showDepChoose = function () {
    showChoose();
    showOverlay();
  };

  // 触发安装：mode = 'local' | 'online' | undefined（沿用上次 / 自动）
  window.triggerDepInstall = function (mode) {
    showRun();
    showOverlay();
    actions.style.display = 'none';
    stage.textContent = '正在启动安装…';
    if (title) title.textContent = '正在安装运行依赖';
    var opts = { method: 'POST' };
    if (mode) {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body = JSON.stringify({ mode: mode });
    }
    fetch('/api/dependencies/install', opts)
      .then(function (r) { return r.json(); })
      .then(applyDep)
      .catch(function () { stage.textContent = '触发安装失败，请刷新后重试'; });
  };

  // 实时进度（socket）
  var depSocket = io({ transports: ['polling'] });
  depSocket.on('dependency_progress', function (d) { applyDep(d); });

  // 初始拉取状态，决定是否弹出遮罩 / 选择卡片
  fetch('/api/dependencies')
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ready) { hideOverlay(); return; }
      if (d.status === 'installing') {
        applyDep(d);            // 已在安装中：直接显示进度
      } else {
        // idle / failed：展示「选择安装方式」卡片
        showOverlay();
        showChoose();
      }
    })
    .catch(function () { /* 未登录或非 JSON 响应：不弹遮罩 */ });
})();
