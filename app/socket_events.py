from flask import request
from flask_socketio import emit
from app.tooldelta_manager import tooldelta_manager, ansi_to_html

def init_socketio(socketio):
    # 注册前清空监听器，避免重复初始化时同一事件被多次广播
    tooldelta_manager.clear_listeners()

    @socketio.on("connect")
    def handle_connect():
        # 鉴权：未登录的 WebSocket 连接直接断开，防止未授权访问控制台（P2-3）
        # fail-closed：会话校验异常（含未登录）一律拒绝连接，避免误放行
        from flask import session
        from flask_socketio import disconnect
        if not session.get("authenticated"):
            disconnect()

    @socketio.on("console_command")
    def handle_command(data):
        # 兼容字符串与 {"cmd": "..."} / {"command": "..."} 两种前端格式
        if isinstance(data, dict):
            cmd = data.get("cmd") or data.get("command") or ""
        elif isinstance(data, str):
            cmd = data
        else:
            cmd = ""
        cmd = (cmd or "").strip()
        if cmd:
            tooldelta_manager.send_command(cmd)

    def broadcast_listener(type_, data):
        if type_ == "output":
            socketio.emit("console_output", {
                "type": "output",
                "data": data,
                "data_html": ansi_to_html(data),
            })
        elif type_ == "system":
            socketio.emit("console_output", {
                "type": "system",
                "data": data,
                "data_html": ansi_to_html(data),
            })

    tooldelta_manager.add_listener(broadcast_listener)
