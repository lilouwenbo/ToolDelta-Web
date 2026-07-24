import os
from datetime import timedelta
from flask import Flask, session, redirect, request
from flask_socketio import SocketIO
from config import Config

socketio = SocketIO()

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    web_data_dir = app.config.get("WEB_DATA_DIR")
    if web_data_dir:
        os.makedirs(web_data_dir, exist_ok=True)
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.config["SESSION_PERMANENT"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
    # 安全 cookie：默认 False 保持本地/HTTP 开发可用，生产环境可通过环境变量强制 HTTPS
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in ("1", "true", "yes")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    from app.routes import main, console, plugins, market, backup, commands, api, logs, auth, files, connections, watchdog, scheduler, dashboard
    app.register_blueprint(main.bp)
    app.register_blueprint(console.bp)
    app.register_blueprint(plugins.bp)
    app.register_blueprint(market.bp)
    app.register_blueprint(backup.bp)
    app.register_blueprint(commands.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(logs.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(files.bp)
    app.register_blueprint(connections.bp)
    app.register_blueprint(watchdog.bp)
    app.register_blueprint(scheduler.bp)
    app.register_blueprint(dashboard.bp)

    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    from app.tooldelta_manager import tooldelta_manager
    tooldelta_manager.init_app(app)

    # 依赖自管模块：初始化上下文，供 socket 事件与 start() 使用
    from app.dependency_service import dependency_service
    dependency_service.init_app(app)

    from app.log_service import log_service
    log_service.init_app(app)

    from . import auth_service as auth_svc
    auth_svc.init_app(app)

    from . import wallpaper_service as wp_svc
    wp_svc.init_app(app)

    from app.socket_events import init_socketio
    init_socketio(socketio)

    # 初始化即解压出厂主程序（让 pyproject.toml 存在），再检测并后台安装运行依赖，
    # 避免全新 Linux 环境“点启动才装、30s 超时装不完、起不来”的问题
    try:
        tooldelta_manager._ensure_main_program()
    except Exception:
        pass
    dependency_service.maybe_auto_install()

    # 新增模块（P1/P2 增强）
    from app import connection_service as conn_svc
    conn_svc.init_app(app)
    from app.watchdog_service import watchdog_service
    watchdog_service.init_app(app)
    from app.scheduler_service import scheduler_service
    scheduler_service.init_app(app)
    from app.dashboard_service import dashboard_service
    dashboard_service.init_app(app)

    @app.before_request
    def check_auth():
        if request.method == "OPTIONS":
            return
        path = request.path
        # 已配置后不应再访问 setup 页面，避免误操作重新初始化
        if auth_svc.is_configured() and (path == "/setup" or path.startswith("/api/setup")):
            return redirect("/")
        allowed_prefixes = ["/login", "/setup", "/api/login", "/api/setup", "/api/reset-panel", "/logout", "/static/"]
        if any(path == p or path.startswith(p) for p in allowed_prefixes):
            return
        if not auth_svc.is_configured():
            if path != "/setup":
                return redirect("/setup")
            return
        if not session.get("authenticated"):
            return redirect("/login")

    @app.context_processor
    def inject_wallpaper():
        return {"wallpaper_url": wp_svc.get_wallpaper()}

    @app.context_processor
    def inject_versions():
        # 注入三版本信息供设置页等模板展示（P2-5）
        try:
            from app.dashboard_service import dashboard_service
            return {"versions": dashboard_service.get_version_info()}
        except Exception:
            return {"versions": {"web_version": "1.0", "build_hash": "nogit", "tooldelta_version": "—"}}

    @app.after_request
    def add_security_headers(response):
        # 基础安全响应头：防点击劫持、MIME 嗅探、XSS 过滤；不强制 HSTS（保留 HTTP 开发可用）
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # 限制前端 JS 能力，防止 XSS 后滥用敏感 API（摄像头/地理位置等）
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

    return app
