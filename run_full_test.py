# -*- coding: utf-8 -*-
"""ToolDelta-Web 全功能端到端测试（隔离环境，不触碰真实 ToolDelta 安装）"""
import os, sys, io, json, shutil, zipfile, time

ROOT = os.path.dirname(os.path.abspath(__file__))
TD = "/tmp/td_fulltest/ToolDelta"
sys.path.insert(0, ROOT)

os.environ["TOOLDELTA_DIR"] = TD

# ---- 1. 清理旧测试产物（仅本面板自己生成的数据目录，非终端程序文件）----
for d in ["backups", "plugin_market", "bridge_plugin", "instance"]:
    p = os.path.join(ROOT, d)
    if os.path.exists(p):
        shutil.rmtree(p, ignore_errors=True)

# ---- 2. 搭建隔离 TOOLDELTA_DIR ----
shutil.rmtree("/tmp/td_fulltest", ignore_errors=True)
os.makedirs(TD, exist_ok=True)
os.makedirs(os.path.join(TD, "插件文件", "ToolDelta类式插件"), exist_ok=True)
os.makedirs(os.path.join(TD, "插件配置文件"), exist_ok=True)
os.makedirs(os.path.join(TD, "插件数据文件"), exist_ok=True)

plugin_dir = os.path.join(TD, "插件文件", "ToolDelta类式插件", "DemoPlugin")
os.makedirs(plugin_dir, exist_ok=True)
with open(os.path.join(plugin_dir, "__init__.py"), "w", encoding="utf-8") as f:
    f.write(
        "# demo plugin\n"
        "import tooldelta\n"
        'tooldelta.add_console_cmd_trigger(["测试命令"], "测试提示", "这是一个测试命令的用法说明")\n'
    )
with open(os.path.join(plugin_dir, "datas.json"), "w", encoding="utf-8") as f:
    json.dump({"author": "tester", "version": "1.0.0", "description": "demo",
               "plugin-id": "demo"}, f, ensure_ascii=False)
with open(os.path.join(TD, "插件配置文件", "DemoPlugin.json"), "w", encoding="utf-8") as f:
    json.dump({"setting_a": 1}, f)

with open(os.path.join(TD, "ToolDelta基本配置.json"), "w", encoding="utf-8") as f:
    json.dump({"全局GitHub镜像": "https://github.com"}, f, ensure_ascii=False)

with open(os.path.join(TD, "main.py"), "w", encoding="utf-8") as f:
    f.write("import sys, time\nprint('ToolDelta mock started')\nsys.stdout.flush()\n"
            "while True:\n    time.sleep(0.3)\n")

# ---- 3. 创建应用与测试客户端 ----
from app import create_app, socketio
app = create_app()
app.config["TESTING"] = True
client = app.test_client()

results = []
def rec(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("  [PASS] " if ok else "  [FAIL] ") + name + (("  -> " + detail) if (detail and not ok) else ""))

def jget(r):
    try:
        v = r.get_json(force=True, silent=True)
        return v if v is not None else {}
    except Exception:
        return {}

def gj(path):
    r = client.get(path)
    return r, jget(r)

def pj(path, payload):
    r = client.post(path, json=payload)
    return r, jget(r)

# ============ A. 初始化与认证 ============
print("\n== A. 初始化与认证 ==")
r = client.get("/")
rec("未配置时 / 跳转 /setup", r.status_code in (301,302) and "/setup" in (r.headers.get("Location") or ""), str(r.status_code))
r, d = pj("/api/setup", {"username": "admin", "password": "admin123"})
rec("初始化面板 /api/setup", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/auth/status")
rec("已配置且已登录", (d.get("data") or {}).get("isConfigured") is True and (d.get("data") or {}).get("authenticated") is True and (d.get("data") or {}).get("role") == 10, json.dumps(d))
for page in ["/", "/files", "/console", "/plugins", "/market", "/backup", "/commands", "/logs", "/settings"]:
    r = client.get(page)
    rec("页面渲染 GET %s" % page, r.status_code == 200, "status=%d" % r.status_code)
r = client.get("/setup")
rec("已配置后 /setup 跳转 /", r.status_code in (301,302) and (r.headers.get("Location") or "").endswith("/"), str(r.status_code))
r = client.get("/login")
rec("已登录后 /login 跳转 /", r.status_code in (301,302) and (r.headers.get("Location") or "").endswith("/"), str(r.status_code))

# ============ B. 文件管理 ============
print("\n== B. 文件管理 ==")
r, d = gj("/api/files/list")
rec("文件列表根目录 list", d.get("success") is True, json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/files/save", {"path": "a.txt", "content": "hello"})
rec("保存文件 save", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/files/read?path=a.txt")
rec("读取文件 read", (d.get("data") or {}).get("content") == "hello", json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/files/mkdir", {"path": "testdir"})
rec("创建目录 mkdir", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/files/rename", {"path": "a.txt", "new_name": "b.txt"})
rec("重命名 rename", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/files/move", {"path": "b.txt", "destination": "testdir/b.txt"})
rec("移动 move", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/files/copy", {"path": "testdir/b.txt", "destination": "testdir/c.txt"})
rec("复制 copy", d.get("success") is True, json.dumps(d, ensure_ascii=False))
buf = io.BytesIO(b"upload content")
r = client.post("/api/files/upload", data={"path": "testdir", "file": (buf, "up.txt")}, content_type="multipart/form-data")
rec("上传文件 upload", jget(r).get("success") is True, json.dumps(jget(r), ensure_ascii=False)[:80])
r = client.get("/api/files/download?path=testdir/c.txt")
rec("下载文件 download", r.status_code == 200, "status=%d" % r.status_code)
r = client.get("/api/files/download-dir?path=testdir")
rec("下载目录 download-dir", r.status_code == 200, "status=%d" % r.status_code)
r, d = gj("/api/files/search?q=b.txt")
rec("搜索文件 search", d.get("success") is True, json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/files/batch-delete", {"paths": ["testdir/c.txt", "testdir/up.txt"]})
rec("批量删除 batch-delete", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/files/delete", {"path": "testdir"})
rec("删除目录 delete", d.get("success") is True, json.dumps(d, ensure_ascii=False))

# ============ C. 用户管理 ============
print("\n== C. 用户管理 ==")
r, d = pj("/api/users/create", {"username": "user1", "password": "user1123", "role": 1})
rec("创建用户 create", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/users")
rec("用户列表 list 含 user1", any(u.get("username") == "user1" for u in (d.get("data") or [])), json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/users/reset-password", {"username": "user1", "password": "newpass1"})
rec("重置用户密码 reset-password", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/change-password", {"old_password": "admin123", "new_password": "admin456"})
rec("修改自身密码 change-password", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/users/delete", {"username": "user1"})
rec("删除用户 delete", d.get("success") is True, json.dumps(d, ensure_ascii=False))

# ============ D. 插件管理 ============
print("\n== D. 插件管理 ==")
r, d = gj("/api/plugins")
rec("插件列表含 DemoPlugin", any(p.get("name") == "DemoPlugin" for p in d), json.dumps(d, ensure_ascii=False)[:100])
r, d = pj("/api/plugins/toggle", {"name": "DemoPlugin", "enable": False})
rec("禁用插件 toggle off", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/plugins")
demo = next((p for p in d if p.get("name") == "DemoPlugin"), {})
rec("插件状态为禁用", demo.get("is_enabled") is False, json.dumps(demo, ensure_ascii=False))
r, d = pj("/api/plugins/toggle", {"name": "DemoPlugin", "enable": True})
rec("启用插件 toggle on", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/plugins/config?name=DemoPlugin")
rec("读取插件配置 config", d.get("setting_a") == 1, json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/plugins/config", {"name": "DemoPlugin", "config": {"setting_a": 99}})
rec("保存插件配置 config POST", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/plugins/readme?name=DemoPlugin")
rec("读取插件 readme（无则友好）", d.get("error") == "未找到文档", json.dumps(d, ensure_ascii=False))
r, d = gj("/api/plugins/data-files?name=DemoPlugin")
rec("插件数据文件列表 data-files", isinstance(d, list), json.dumps(d, ensure_ascii=False)[:80])
buf = io.BytesIO(b"data content")
r = client.post("/api/plugins/data-upload", data={"name": "DemoPlugin", "file": (buf, "d.txt")}, content_type="multipart/form-data")
rec("上传数据文件 data-upload", jget(r).get("success") is True, json.dumps(jget(r), ensure_ascii=False)[:80])
r, d = pj("/api/plugins/data-delete", {"name": "DemoPlugin", "file": "d.txt"})
rec("删除数据文件 data-delete", d.get("success") is True, json.dumps(d, ensure_ascii=False))
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    z.writestr("TestPlugin2/__init__.py", "# tp2\n")
    z.writestr("TestPlugin2/datas.json", json.dumps({"plugin-id": "TestPlugin2", "author": "t", "version": "1.0", "description": "t"}))
buf.seek(0)
r = client.post("/api/plugins/upload", data={"file": (buf, "TestPlugin2.zip")}, content_type="multipart/form-data")
rec("上传插件 zip upload", jget(r).get("success") is True, json.dumps(jget(r), ensure_ascii=False)[:80])
r, d = gj("/api/plugins")
rec("上传后插件列表含 TestPlugin2", any(p.get("name") == "TestPlugin2" for p in d), json.dumps(d, ensure_ascii=False)[:100])
r, d = pj("/api/plugins/delete", {"name": "TestPlugin2"})
rec("删除插件 delete", d.get("success") is True, json.dumps(d, ensure_ascii=False))

# ============ E. 备份 ============
print("\n== E. 备份 ==")
r, d = pj("/api/backup/create", {"name": "bak1"})
rec("创建备份 create", d.get("success") is True or "zip" in d, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/backups")
rec("备份列表含 bak1", any(b.get("name") == "bak1" for b in d), json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/backup/restore", {"zip": "bak1.zip"})
rec("恢复备份 restore", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/backup/delete", {"zip": "bak1.zip"})
rec("删除备份 delete", d.get("success") is True, json.dumps(d, ensure_ascii=False))

# ============ F. 命令扫描 ============
print("\n== F. 命令扫描 ==")
r, d = gj("/api/commands")
rec("命令列表 commands", isinstance(d, list), json.dumps(d, ensure_ascii=False)[:80])
r = client.get("/api/commands/plugin?name=DemoPlugin")
rec("按插件查命令 commands/plugin", r.status_code == 200, "status=%d" % r.status_code)
r, d = gj("/api/commands/stats")
rec("命令统计 stats", "total_commands" in (d or {}), json.dumps(d, ensure_ascii=False)[:80])

# ============ G0. 修复验证：空目录启动自动解压出厂包 ============
# 验证：当 TOOLDELTA_DIR 为空（首次部署/初始化时压缩包未解压）时，
# start() 会自动从出厂包解压 main.py，而不是失败返回。
print("\n== G0. 修复：空目录启动自动解压 ==")
import tempfile as _tempfile
from app.tooldelta_manager import tooldelta_manager as _mgr
_td_auto = _tempfile.mkdtemp(prefix="td_auto_")
_app_auto = create_app()
_app_auto.config["TOOLDELTA_DIR"] = _td_auto
_app_auto.config["TOOLDELTA_MAIN"] = os.path.join(_td_auto, "main.py")
_mgr.app = _app_auto
_ok_auto, _msg_auto = _mgr._ensure_main_program()
rec("空目录自动解压出厂包生成 main.py", _ok_auto and os.path.isfile(_app_auto.config["TOOLDELTA_MAIN"]), str(_msg_auto))
# 恢复全局 mgr 指向主测试 app，避免影响后续 G 部分
_mgr.app = app

# ============ G1. 深层：main.py 损坏后自动重新解压恢复 ============
print("\n== G1. 深层：main.py 损坏恢复 ==")
import tempfile as _tf
_td_dmg = _tf.mkdtemp(prefix="td_dmg_")
_app_dmg = create_app()
_app_dmg.config["TOOLDELTA_DIR"] = _td_dmg
_app_dmg.config["TOOLDELTA_MAIN"] = os.path.join(_td_dmg, "main.py")
from app.tooldelta_manager import tooldelta_manager as _mgr
_mgr.app = _app_dmg
_ok1, _msg1 = _mgr._ensure_main_program()
rec("先解压出厂包 main.py 有效", _ok1 and _mgr._is_valid_main(_app_dmg.config["TOOLDELTA_MAIN"]), str(_msg1))
with open(_app_dmg.config["TOOLDELTA_MAIN"], "w") as f:
    f.write("")  # 模拟损坏（清空）
rec("损坏后 _is_valid_main 识别为无效", _mgr._is_valid_main(_app_dmg.config["TOOLDELTA_MAIN"]) is False, "")
_ok2, _msg2 = _mgr._ensure_main_program()
rec("损坏后自动重新解压恢复成功", _ok2 and _mgr._is_valid_main(_app_dmg.config["TOOLDELTA_MAIN"]), str(_msg2))
_mgr.app = app

# ============ G. 进程管理 ============
print("\n== G. 进程管理 ==")
r, d = pj("/api/tool/command", {"cmd": "help"})
rec("未启动时命令失败 command", d.get("success") is False, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/status")
rec("初始状态未运行 status", (d or {}).get("running") is False, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/tool/start", {})
rec("启动进程 start", d.get("success") is True, json.dumps(d, ensure_ascii=False))
time.sleep(1.0)
r, d = gj("/api/status")
rec("启动后状态 running", (d or {}).get("running") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/tool/command", {"cmd": "help"})
rec("运行后命令成功 command", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r = client.get("/api/tool/output?tail=50")
lines = jget(r).get("lines", [])
rec("读取输出 output 含 mock", any("ToolDelta mock" in (l or "") for l in lines), json.dumps(lines, ensure_ascii=False)[:80])
r, d = pj("/api/tool/restart", {})
rec("重启进程 restart", d.get("success") is True, json.dumps(d, ensure_ascii=False))
time.sleep(0.8)
r, d = pj("/api/tool/stop", {})
rec("停止进程 stop", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/status")
rec("停止后状态未运行", (d or {}).get("running") is False, json.dumps(d, ensure_ascii=False))
# 深层：异常输入健壮性
r, d = pj("/api/tool/start", {})
rec("再次启动 start(停止态)", d.get("success") is True, json.dumps(d, ensure_ascii=False))
time.sleep(0.8)
r, d = pj("/api/tool/start", {})  # 已运行时重复启动
rec("已运行时重复 start 仍返回 True", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/tool/stop", {})
rec("停止进程 stop(第2次)", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/tool/stop", {})  # 未运行时再停止
rec("未运行时 stop 返回 True(不报错)", d.get("success") is True, json.dumps(d, ensure_ascii=False))

# ============ H. 市场 ============
print("\n== H. 市场 ==")
r, d = gj("/api/market/plugins")
rec("市场插件列表 market/plugins", isinstance(d, list), json.dumps(d, ensure_ascii=False)[:80])
r, d = gj("/api/market/packages")
rec("市场包列表 market/packages", isinstance(d, list), json.dumps(d, ensure_ascii=False)[:80])
r, d = gj("/api/plugins/presets")
rec("预设插件 presets", isinstance(d, list), json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/plugins/install-preset", {"plugin_id": "not_exist_xyz"})
rec("安装不存在预设(友好失败) install-preset", d.get("success") is False, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/plugins/install-preset-batch", {"plugin_ids": ["not_exist_xyz"]})
rec("批量安装预设(友好失败) install-preset-batch", isinstance((d or {}).get("results"), list), json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/market/connect", {"url": ""})
rec("市场连接空url(友好失败) market/connect", d.get("success") is False, json.dumps(d, ensure_ascii=False))

# ============ I. 日志 ============
print("\n== I. 日志 ==")
r, d = gj("/api/logs")
rec("今日日志 logs", "lines" in (d or {}), json.dumps(d, ensure_ascii=False)[:80])
r, d = gj("/api/logs/files")
rec("日志文件列表 logs/files", isinstance(d, list), json.dumps(d, ensure_ascii=False)[:80])
today = time.strftime("%Y-%m-%d")
r, d = gj("/api/logs/file?date=" + today)
rec("读取某日日志 logs/file", "lines" in (d or {}), json.dumps(d, ensure_ascii=False)[:80])

# ============ J. 系统/配置 ============
print("\n== J. 系统/配置 ==")
r, d = gj("/api/system/info")
rec("系统信息 system/info", (d or {}).get("tooldelta_dir") == TD, json.dumps(d, ensure_ascii=False)[:100])
r, d = gj("/api/launcher/config")
rec("启动器配置 launcher/config", (d or {}).get("全局GitHub镜像") == "https://github.com", json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/launcher/config", {"custom_key": 123})
rec("保存启动器配置 launcher/config POST", d.get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/fbtoken")
rec("读取 fbtoken", "token" in (d or {}), json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/fbtoken", {"token": "abc123"})
rec("保存 fbtoken", d.get("success") is True, json.dumps(d, ensure_ascii=False))

# ============ K. 壁纸 ============
print("\n== K. 壁纸 ==")
r, d = gj("/api/settings/wallpaper")
rec("获取壁纸 wallpaper", "url" in ((d or {}).get("data") or {}), json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/settings/wallpaper/fetch", {"url": "http://example.com/x.png"})
rec("手动设置壁纸 fetch", d.get("success") is True, json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/settings/wallpaper/clear", {})
rec("清除壁纸 clear", d.get("success") is True, json.dumps(d, ensure_ascii=False))

# ============ L. 权限（普通用户）============
print("\n== L. 权限校验（普通用户）==")
r, d = pj("/api/users/create", {"username": "user2", "password": "user2123", "role": 1})
rec("创建普通用户 user2", d.get("success") is True, json.dumps(d, ensure_ascii=False))
client_user = app.test_client()
r = client_user.post("/api/login", json={"username": "user2", "password": "user2123"})
rec("普通用户登录", (jget(r).get("success") is True), json.dumps(jget(r), ensure_ascii=False))
r = client_user.post("/api/reset", json={})
rec("普通用户禁止 reset", jget(r).get("error") == "无权限", json.dumps(jget(r), ensure_ascii=False))
r = client_user.post("/api/backup/restore", json={"zip": "bak1.zip"})
rec("普通用户禁止 restore", jget(r).get("error") == "无权限", json.dumps(jget(r), ensure_ascii=False))
r = client_user.post("/api/backup/delete", json={"zip": "bak1.zip"})
rec("普通用户禁止 delete", jget(r).get("error") == "无权限", json.dumps(jget(r), ensure_ascii=False))

# ============ M. 空 body 健壮性 ============
print("\n== M. 空 body 健壮性（不应 500）==")
r = client.post("/api/login", data="", content_type="application/json")
rec("空body login 不500", r.status_code != 500, "status=%d" % r.status_code)
r = client.post("/api/plugins/toggle", data="", content_type="application/json")
rec("空body toggle 不500", r.status_code != 500, "status=%d" % r.status_code)
r = client.post("/api/launcher/config", data="", content_type="application/json")
rec("空body launcher/config 不500", r.status_code != 500, "status=%d" % r.status_code)
r = client.post("/api/backup/create", data="", content_type="application/json")
rec("空body backup/create 不500", r.status_code != 500, "status=%d" % r.status_code)

# ============ N. WebSocket ============
print("\n== N. WebSocket 事件 ==")
try:
    sio = socketio.test_client(app)
    sio.emit("console_command", "help")
    sio.disconnect()
    rec("WebSocket connect/console_command/disconnect", True)
except Exception as e:
    rec("WebSocket connect/console_command/disconnect", False, str(e)[:120])

# ============ P. 统一命令库与收藏（P0 新功能）============
print("\n== P. 统一命令库与收藏 ==")
# 确保从干净状态开始（按用户隔离，容错清理历史残留）
_fav0 = gj("/api/favorites")[1].get("commands") or []
for _c in _fav0:
    client.delete("/api/favorites", json={"cmd": _c})

# — 统一命令库：静态扫描 + 运行时注册表合并 —
r, d = gj("/api/commands")
rec("命令库返回数组", isinstance(d, list), json.dumps(d, ensure_ascii=False)[:80])
_has_triggers = any(isinstance(p.get("commands"), list) and p["commands"] and isinstance(p["commands"][0].get("triggers"), list) for p in (d or []))
rec("命令库含触发器 triggers", _has_triggers, json.dumps(d, ensure_ascii=False)[:80])
r, d = gj("/api/commands/stats")
rec("命令统计 total_commands/total_plugins", ("total_commands" in (d or {})) and ("total_plugins" in (d or {})), json.dumps(d, ensure_ascii=False)[:80])
r = client.get("/api/commands/plugin?name=DemoPlugin")
rec("按插件查命令 commands/plugin", r.status_code == 200, "status=%d" % r.status_code)

# — 命令收藏：用户级增删查 + 健壮性 —
r, d = gj("/api/favorites")
rec("收藏列表初始为数组", isinstance((d or {}).get("commands"), list), json.dumps(d, ensure_ascii=False))
r, d = pj("/api/favorites", {"cmd": "help"})
rec("收藏添加 POST", (d or {}).get("success") is True and "help" in ((d or {}).get("commands") or []), json.dumps(d, ensure_ascii=False))
r, d = pj("/api/favorites", {"cmd": "help"})
rec("收藏重复添加幂等", (d or {}).get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/favorites", {"cmd": "stop"})
rec("收藏添加第二条 stop", (d or {}).get("success") is True and "stop" in ((d or {}).get("commands") or []), json.dumps(d, ensure_ascii=False))
r, d = gj("/api/favorites")
rec("收藏列表含 help/stop", set((d or {}).get("commands") or []) >= {"help", "stop"}, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/favorites", {"cmd": ""})
rec("收藏空命令被拒", (d or {}).get("success") is False, json.dumps(d, ensure_ascii=False))
r = client.delete("/api/favorites", json={"cmd": "help"})
d = jget(r)
rec("收藏删除 DELETE help", (d or {}).get("success") is True and "help" not in ((d or {}).get("commands") or []), json.dumps(d, ensure_ascii=False))
# 清理 stop，保证每轮结束为空（不影响跨轮/后续段）
client.delete("/api/favorites", json={"cmd": "stop"})

# ============ O. 管理员恢复出厂（深层：连续3次一致性）============
print("\n== O. 管理员恢复出厂（连续3次）==")
_main_o = app.config["TOOLDELTA_MAIN"]
for _ri in range(1, 4):
    r, d = pj("/api/reset", {})
    rec("管理员 reset 成功 #%d" % _ri, d.get("success") is True, json.dumps(d, ensure_ascii=False))
    rec("reset #%d 后 main.py 存在且有效" % _ri, os.path.isfile(_main_o) and _mgr._is_valid_main(_main_o), "")

try:
    from app.tooldelta_manager import tooldelta_manager
    tooldelta_manager.stop()
except Exception:
    pass

# ============ Q. P1/P2 新增模块（本次迭代）============
print("\n== Q. P1/P2 新增模块 ==")

# --- Q1. 服务器连接配置 ---
r, d = gj("/api/connections")
rec("连接列表初始为数组", isinstance(d, list), json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/connections/add", {"name": "测试服", "host": "127.0.0.1", "port": 19132, "protocol": "tcp"})
rec("添加连接 add", (d or {}).get("success") is True and "conn" in (d or {}), json.dumps(d, ensure_ascii=False))
_conn_id = (d.get("conn") or {}).get("id")
r, d = gj("/api/connections")
rec("连接列表含新连接", isinstance(d, list) and any((c.get("id") == _conn_id) for c in d), json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/connections/update", {"id": _conn_id, "name": "改名服"})
rec("更新连接 update", (d or {}).get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/connections/default", {"id": _conn_id})
rec("设为默认 default", (d or {}).get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/connections")
rec("默认连接标记正确", any((c.get("id") == _conn_id and c.get("is_default") is True) for c in d), json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/connections/delete", {"id": _conn_id})
rec("删除连接 delete", (d or {}).get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/connections")
rec("删除后列表不含该连接", isinstance(d, list) and not any((c.get("id") == _conn_id) for c in d), json.dumps(d, ensure_ascii=False)[:80])
r = client.get("/connections")
rec("页面渲染 GET /connections", r.status_code == 200, "status=%d" % r.status_code)

# --- Q2. 看门狗（仅验证配置/状态，不启用以避免启动真实进程）---
r, d = gj("/api/watchdog/config")
rec("看门狗配置初始 enabled=False", isinstance(d, dict) and d.get("enabled") is False, json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/watchdog/set", {"check_interval": 5, "auto_restart": True, "max_restarts": 3, "restart_cooldown": 10})
rec("保存看门狗配置 set", (d or {}).get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = gj("/api/watchdog/config")
rec("看门狗配置已更新 check_interval=5", (d or {}).get("check_interval") == 5, json.dumps(d, ensure_ascii=False)[:80])
r, d = gj("/api/watchdog/status")
rec("看门狗状态含运行时字段", isinstance(d, dict) and ("enabled" in d) and ("monitor_running" in d), json.dumps(d, ensure_ascii=False)[:80])
r = client.get("/watchdog")
rec("页面渲染 GET /watchdog", r.status_code == 200, "status=%d" % r.status_code)

# --- Q3. 定时任务（不启用自动调度，仅验证 CRUD + 立即运行）---
r, d = gj("/api/scheduler/jobs")
rec("任务列表初始为数组", isinstance(d, list), json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/scheduler/add", {"name": "每日备份", "type": "daily", "hour": 3, "minute": 0, "command": "backup", "enabled": False})
rec("添加任务 add", (d or {}).get("success") is True and "job" in (d or {}), json.dumps(d, ensure_ascii=False))
_job_id = (d.get("job") or {}).get("id")
r, d = gj("/api/scheduler/jobs")
rec("任务列表含新任务", isinstance(d, list) and any((j.get("id") == _job_id) for j in d), json.dumps(d, ensure_ascii=False)[:80])
r, d = pj("/api/scheduler/run", {"id": _job_id})
rec("立即运行任务 run", (d or {}).get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/scheduler/update", {"id": _job_id, "enabled": False})
rec("更新任务 update(保持禁用)", (d or {}).get("success") is True, json.dumps(d, ensure_ascii=False))
r, d = pj("/api/scheduler/delete", {"id": _job_id})
rec("删除任务 delete", (d or {}).get("success") is True, json.dumps(d, ensure_ascii=False))
r = client.get("/scheduler")
rec("页面渲染 GET /scheduler", r.status_code == 200, "status=%d" % r.status_code)

# --- Q4. 状态仪表盘 ---
r, d = gj("/api/dashboard")
rec("仪表盘聚合含 system/tooldelta/panel", isinstance(d, dict) and ("system" in d) and ("tooldelta" in d) and ("panel" in d), json.dumps(d, ensure_ascii=False)[:80])

# --- Q5. 日志增强 ---
r, d = gj("/api/logs/query")
rec("日志查询返回 lines/sources", isinstance(d, dict) and isinstance(d.get("lines"), list) and isinstance(d.get("sources"), list), json.dumps(d, ensure_ascii=False)[:80])
r, d = gj("/api/logs/sources")
rec("日志来源列表为数组", isinstance(d, list), json.dumps(d, ensure_ascii=False)[:80])
r = client.get("/api/logs/export")
rec("日志导出返回文本", r.status_code == 200 and (r.headers.get("Content-Type") or "").startswith("text/plain"), "status=%d" % r.status_code)

passed = sum(1 for _, ok, _ in results if ok)
failed = [n for n, ok, _ in results if not ok]
print("\n========================================")
print("测试结果: %d 通过 / %d 失败 (共 %d)" % (passed, len(failed), len(results)))
if failed:
    print("失败项:")
    for f in failed:
        print("  - " + f)
else:
    print("全部功能测试通过")
print("========================================")

shutil.rmtree("/tmp/td_fulltest", ignore_errors=True)
for d in ["backups", "plugin_market", "bridge_plugin", "instance"]:
    p = os.path.join(ROOT, d)
    if os.path.exists(p):
        shutil.rmtree(p, ignore_errors=True)
print("已清理临时测试产物。")
