import os
import json
from flask import Blueprint, request, jsonify, current_app, session
from app.tooldelta_manager import tooldelta_manager
from app.plugin_service import plugin_service
from app.market_service import market_service
from app.backup_service import backup_service
from app.cmd_scanner import cmd_scanner
from app.log_service import log_service

bp = Blueprint("api", __name__, url_prefix="/api")

def audit(action, detail=""):
    user = session.get("username", "?")
    ip = request.remote_addr or "?"
    log_service.info(f"[{user}@{ip}] {action} {detail}", "AUDIT")

# ─── ToolDelta 进程管理 ────────────────────────

@bp.route("/status")
def status():
    s = tooldelta_manager.get_status()
    return jsonify(s)

@bp.route("/tool/start", methods=["POST"])
def tool_start():
    ok = tooldelta_manager.start()
    if ok: audit("启动 ToolDelta")
    return jsonify({"success": ok})

@bp.route("/tool/stop", methods=["POST"])
def tool_stop():
    ok = tooldelta_manager.stop()
    if ok: audit("停止 ToolDelta")
    return jsonify({"success": ok})

@bp.route("/tool/restart", methods=["POST"])
def tool_restart():
    ok = tooldelta_manager.restart()
    if ok: audit("重启 ToolDelta")
    return jsonify({"success": ok})

@bp.route("/tool/command", methods=["POST"])
def tool_command():
    data = request.get_json(silent=True) or {}
    cmd = data.get("cmd", "")
    if not cmd:
        return jsonify({"success": False, "error": "命令不能为空"})
    ok = tooldelta_manager.send_command(cmd)
    return jsonify({"success": ok})

@bp.route("/tool/output")
def tool_output():
    tail = request.args.get("tail", 200, type=int)
    as_html = request.args.get("html", "0") == "1"
    return jsonify({"lines": tooldelta_manager.get_output(tail, as_html=as_html)})

# ─── 插件管理 ────────────────────────

@bp.route("/plugins")
def list_plugins():
    return jsonify(plugin_service.list_plugins())

@bp.route("/plugins/toggle", methods=["POST"])
def toggle_plugin():
    data = request.get_json(silent=True) or {}
    name, enable = data.get("name"), data.get("enable")
    if not name:
        return jsonify({"success": False, "error": "缺少插件名"})
    ok = plugin_service.toggle_plugin(name, enable)
    if ok: audit("切换插件", f"{name} -> {'启用' if enable else '禁用'}")
    return jsonify({"success": ok})

@bp.route("/plugins/delete", methods=["POST"])
def delete_plugin():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"success": False, "error": "缺少插件名"})
    ok = plugin_service.delete_plugin(name)
    if ok: audit("删除插件", f"插件={name}")
    return jsonify({"success": ok})

@bp.route("/plugins/upload", methods=["POST"])
def upload_plugin():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "未上传文件"})
    f = request.files["file"]
    if not f.filename.endswith(".zip"):
        return jsonify({"success": False, "error": "仅支持 .zip 文件"})
    try:
        plugin_service.upload_plugin(f)
        audit("上传插件", f"文件={f.filename}")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@bp.route("/plugins/readme")
def plugin_readme():
    name = request.args.get("name")
    if not name:
        return jsonify({"error": "缺少插件名"})
    return jsonify(plugin_service.get_plugin_readme(name) or {"error": "未找到文档"})

@bp.route("/plugins/config")
def plugin_config():
    name = request.args.get("name")
    if not name:
        return jsonify({"error": "缺少插件名"})
    return jsonify(plugin_service.get_plugin_config(name) or {"error": "无配置文件"})

@bp.route("/plugins/config", methods=["POST"])
def save_plugin_config():
    data = request.get_json(silent=True) or {}
    name, config = data.get("name"), data.get("config")
    if not name or not config:
        return jsonify({"success": False, "error": "缺少参数"})
    plugin_service.save_plugin_config(name, config)
    return jsonify({"success": True})

@bp.route("/plugins/data-files")
def plugin_data_files():
    name = request.args.get("name")
    if not name:
        return jsonify({"error": "缺少插件名"})
    return jsonify(plugin_service.get_plugin_data_files(name))

@bp.route("/plugins/data-upload", methods=["POST"])
def upload_data_file():
    name = request.form.get("name")
    if not name:
        return jsonify({"success": False, "error": "缺少插件名"})
    if "file" not in request.files:
        return jsonify({"success": False, "error": "未上传文件"})
    f = request.files["file"]
    plugin_service.upload_data_file(name, f)
    return jsonify({"success": True})

@bp.route("/plugins/data-delete", methods=["POST"])
def delete_data_file():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    filename = data.get("file")
    if not name or not filename:
        return jsonify({"success": False, "error": "缺少参数"})
    ok = plugin_service.delete_data_file(name, filename)
    return jsonify({"success": ok})

@bp.route("/plugins/config-upload", methods=["POST"])
def upload_config_file():
    name = request.form.get("name")
    if not name:
        return jsonify({"success": False, "error": "缺少插件名"})
    if "file" not in request.files:
        return jsonify({"success": False, "error": "未上传文件"})
    f = request.files["file"]
    plugin_service.upload_config_file(name, f)
    return jsonify({"success": True})

# ─── 预设/网络 安装 ────────────────────────

@bp.route("/plugins/presets")
def preset_plugins():
    return jsonify(market_service.get_plugins(refresh=True))

@bp.route("/plugins/install-preset", methods=["POST"])
def install_preset():
    data = request.get_json(silent=True) or {}
    plugin_id = data.get("plugin_id")
    if not plugin_id:
        return jsonify({"success": False, "error": "缺少插件ID"})
    ok, msg = plugin_service.install_preset_plugin(plugin_id)
    if ok: audit("安装预设插件", f"插件ID={plugin_id}")
    return jsonify({"success": ok, "message": msg})

@bp.route("/plugins/install-preset-batch", methods=["POST"])
def install_preset_batch():
    data = request.get_json(silent=True) or {}
    ids = data.get("plugin_ids", [])
    results = plugin_service.install_preset_plugins_batch(ids)
    return jsonify({"results": results})

@bp.route("/plugins/install-network", methods=["POST"])
def install_network():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").rstrip("/")
    plugin_id = data.get("plugin_id")
    if not url or not plugin_id:
        return jsonify({"success": False, "error": "缺少 market_url 或 plugin_id"})
    ok, msg = plugin_service.install_network_plugin(url, plugin_id)
    return jsonify({"success": ok, "message": msg})

@bp.route("/market/connect", methods=["POST"])
def market_connect():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").rstrip("/")
    try:
        import requests
        r = requests.get(f"{url}/market_tree.json", timeout=10)
        r.raise_for_status()
        tree = r.json()
        plugins_list = []
        for pid, info in tree.get("MarketPlugins", {}).items():
            plugins_list.append({
                "id": pid,
                "name": info.get("name", pid),
                "version": info.get("version", "?"),
                "author": info.get("author", "?"),
                "plugin_type": info.get("plugin-type", "classic"),
            })
        return jsonify({"success": True, "source_name": tree.get("SourceName", url), "plugins": plugins_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ─── 插件市场 ────────────────────────

@bp.route("/market/plugins")
def market_plugins():
    market_service.scan()
    by = request.args.get("by", "name")
    kw = request.args.get("q", "")
    if kw:
        return jsonify(market_service.search(kw, by))
    return jsonify(market_service.get_plugins())

@bp.route("/market/packages")
def market_packages():
    market_service.scan()
    return jsonify(market_service.get_packages())

@bp.route("/market/plugin")
def market_plugin_detail():
    pid = request.args.get("id")
    if not pid:
        return jsonify({"error": "缺少插件ID"})
    return jsonify(market_service.get_plugin_data(pid, refresh=True) or {"error": "未找到"})

# ─── 命令扫描 ────────────────────────

@bp.route("/commands")
def list_commands():
    results = cmd_scanner.scan_all_plugins()
    kw = request.args.get("q", "").lower()
    plugin_filter = request.args.get("plugin", "").lower()
    if kw:
        filtered = []
        for p in results:
            matched_cmds = [c for c in p["commands"] if kw in " ".join(c["triggers"]).lower() or kw in c.get("usage", "").lower()]
            if matched_cmds:
                filtered.append({**p, "commands": matched_cmds, "count": len(matched_cmds)})
        results = filtered
    if plugin_filter:
        results = [p for p in results if plugin_filter in p["plugin"].lower()]
    return jsonify(results)

@bp.route("/commands/plugin")
def commands_by_plugin():
    name = request.args.get("name")
    if not name:
        return jsonify({"error": "缺少插件名"})
    return jsonify(cmd_scanner.scan_by_plugin(name))

@bp.route("/commands/stats")
def commands_stats():
    results = cmd_scanner.scan_all_plugins()
    total_cmds = sum(p["count"] for p in results)
    total_plugins = len(results)
    return jsonify({"total_commands": total_cmds, "total_plugins": total_plugins, "plugins": results})

# ─── 命令收藏（用户级，存于 Web 数据目录的 favorites.json） ────────────────
def _fav_path():
    base = current_app.config.get("WEB_DATA_DIR")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "favorites.json")

def _load_fav():
    try:
        with open(_fav_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_fav(data):
    with open(_fav_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _user_favs():
    user = session.get("username") or "default"
    return _load_fav().get(user, [])

def _set_user_favs(cmds):
    user = session.get("username") or "default"
    data = _load_fav()
    data[user] = cmds
    _save_fav(data)

@bp.route("/favorites", methods=["GET"])
def list_favorites():
    return jsonify({"commands": _user_favs()})

@bp.route("/favorites", methods=["POST"])
def add_favorite():
    data = request.get_json(silent=True) or {}
    cmd = (data.get("cmd") or "").strip()
    if not cmd:
        return jsonify({"success": False, "error": "命令不能为空"})
    cmds = _user_favs()
    if cmd not in cmds:
        cmds.append(cmd)
        _set_user_favs(cmds)
    return jsonify({"success": True, "commands": cmds})

@bp.route("/favorites", methods=["DELETE"])
def remove_favorite():
    data = request.get_json(silent=True) or {}
    cmd = (data.get("cmd") or "").strip()
    if not cmd:
        return jsonify({"success": False, "error": "命令不能为空"})
    cmds = [c for c in _user_favs() if c != cmd]
    _set_user_favs(cmds)
    return jsonify({"success": True, "commands": cmds})

# ─── 备份 ────────────────────────

@bp.route("/backups")
def list_backups():
    return jsonify(backup_service.list_backups())

@bp.route("/backup/create", methods=["POST"])
def create_backup():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    meta = backup_service.create_backup(name)
    audit("创建备份", f"名称={meta.get('name','?')}")
    return jsonify(meta)

@bp.route("/backup/restore", methods=["POST"])
def restore_backup():
    if session.get("role") != 10:
        return jsonify({"success": False, "error": "无权限"})
    data = request.get_json(silent=True) or {}
    zip_name = data.get("zip")
    if not zip_name:
        return jsonify({"success": False, "error": "缺少备份文件名"})
    ok, msg = backup_service.restore_backup(zip_name)
    return jsonify({"success": ok, "message": msg})

@bp.route("/backup/delete", methods=["POST"])
def delete_backup():
    if session.get("role") != 10:
        return jsonify({"success": False, "error": "无权限"})
    data = request.get_json(silent=True) or {}
    zip_name = data.get("zip")
    if not zip_name:
        return jsonify({"success": False, "error": "缺少备份文件名"})
    backup_service.delete_backup(zip_name)
    return jsonify({"success": True})

@bp.route("/reset", methods=["POST"])
def reset_to_factory():
    if session.get("role") != 10:
        return jsonify({"success": False, "error": "无权限"})
    ok, msg = backup_service.reset_to_factory()
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg})

# ─── 日志 ────────────────────────

@bp.route("/logs")
def get_logs():
    tail = request.args.get("tail", 200, type=int)
    return jsonify({"lines": log_service.get_today_logs(tail)})

@bp.route("/logs/files")
def log_files():
    return jsonify(log_service.list_log_files())

@bp.route("/logs/file")
def log_file():
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "缺少日期参数"})
    return jsonify({"lines": log_service.get_log_file(date), "date": date})

# ─── 系统信息 ────────────────────────

@bp.route("/system/info")
def system_info():
    import sys, platform
    td_dir = current_app.config["TOOLDELTA_DIR"]
    plugins = plugin_service.list_plugins()
    return jsonify({
        "python_version": sys.version,
        "platform": platform.platform(),
        "tooldelta_dir": td_dir,
        "tooldelta_exists": os.path.isfile(current_app.config["TOOLDELTA_MAIN"]),
        "plugin_count": len(plugins),
        "enabled_plugins": sum(1 for p in plugins if p["is_enabled"]),
    })

# ─── 配置页面 ────────────────────────

@bp.route("/launcher/config")
def launcher_config():
    td_dir = current_app.config["TOOLDELTA_DIR"]
    cfg_path = os.path.join(td_dir, "ToolDelta基本配置.json")
    if os.path.isfile(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({})

@bp.route("/launcher/config", methods=["POST"])
def save_launcher_config():
    data = request.get_json(silent=True) or {}
    td_dir = current_app.config["TOOLDELTA_DIR"]
    cfg_path = os.path.join(td_dir, "ToolDelta基本配置.json")
    current = {}
    if os.path.isfile(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            current = json.load(f)
    current["全局GitHub镜像"] = current.get("全局GitHub镜像", "")
    for k, v in data.items():
        current[k] = v
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    return jsonify({"success": True})

@bp.route("/fbtoken")
def get_fbtoken():
    td_dir = current_app.config["TOOLDELTA_DIR"]
    token_path = os.path.join(td_dir, "fbtoken")
    token = ""
    if os.path.isfile(token_path):
        with open(token_path, "r", encoding="utf-8") as f:
            token = f.read().strip()
    return jsonify({"token": token})

@bp.route("/fbtoken", methods=["POST"])
def save_fbtoken():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    td_dir = current_app.config["TOOLDELTA_DIR"]
    token_path = os.path.join(td_dir, "fbtoken")
    with open(token_path, "w", encoding="utf-8") as f:
        f.write(token)
    audit("更新 fbtoken")
    return jsonify({"success": True})
