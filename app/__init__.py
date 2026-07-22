import os
from datetime import timedelta
from flask import Flask, session, redirect, request
from flask_socketio import SocketIO
from config import Config

socketio = SocketIO()

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    os.makedirs(app.config.get("WEB_DATA_DIR"), exist_ok=True)
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.config["SESSION_PERMANENT"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    from app.routes import main, console, plugins, market, backup, commands, api, logs, auth, files
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

    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    from app.tooldelta_manager import tooldelta_manager
    tooldelta_manager.init_app(app)

    from app.log_service import log_service
    log_service.init_app(app)

    from . import auth_service as auth_svc
    auth_svc.init_app(app)

    from . import wallpaper_service as wp_svc
    wp_svc.init_app(app)

    from app.socket_events import init_socketio
    init_socketio(socketio)

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

    return app
