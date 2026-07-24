# ruff: noqa: E402
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, socketio
from config import Config

if __name__ == "__main__":
    app = create_app()
    # 反代场景（如 nginx）下修正 remote_addr，使登录限流按真实客户端 IP 生效（P2-8）
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    print("[ToolDelta Web] 管理面板启动于 http://%s:%s" % (Config.HOST, Config.PORT))
    print("[ToolDelta Web] 工作目录: %s" % Config.TOOLDELTA_DIR)
    print("[ToolDelta Web] 插件市场: %s" % Config.PLUGIN_MARKET_DIR)
    socketio.run(app, host=Config.HOST, port=Config.PORT, debug=False, allow_unsafe_werkzeug=True)
