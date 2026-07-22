"""服务器连接配置服务（模块函数 + init_app 风格）。

持久化：<instance_path>/server_conn.json，结构为对象数组。
并发安全：使用 threading.Lock + 原子写（临时文件 + os.replace）。
"""
import os
import json
import uuid
import threading
from datetime import datetime

# 全局文件句柄（由 init_app 设置），未初始化时为 None
_FILE = None
_LOCK = threading.Lock()

# 允许的协议
PROTOCOLS = ("tcp", "ws")


def init_app(app):
    """根据 app.instance_path 设置持久化文件路径并创建目录。"""
    global _FILE
    _FILE = os.path.join(app.instance_path, "server_conn.json")
    os.makedirs(os.path.dirname(_FILE), exist_ok=True)


def _read_all():
    """读取全部连接；文件不存在或损坏时返回空列表。"""
    if not _FILE or not os.path.isfile(_FILE):
        return []
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except Exception:
        return []


def _write_all(conns):
    """原子写：先写临时文件，再 os.replace 覆盖。"""
    if not _FILE:
        return
    d = os.path.dirname(_FILE)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, ".server_conn.tmp." + uuid.uuid4().hex)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(conns, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, _FILE)


def list_connections():
    """返回全部连接（深拷贝，避免外部修改缓存）。"""
    with _LOCK:
        return [dict(c) for c in _read_all()]


def get_connection(conn_id):
    """按 id 获取单个连接，不存在返回 None。"""
    with _LOCK:
        for c in _read_all():
            if c.get("id") == conn_id:
                return dict(c)
    return None


def add_connection(payload):
    """新增一个连接，返回创建后的对象。

    payload 至少应含 name/host/port（由路由层校验）。
    其余字段（protocol/token/note）可选，is_default 默认 False。
    """
    if payload is None:
        payload = {}
    name = payload.get("name", "")
    host = payload.get("host", "")
    port = payload.get("port")
    protocol = payload.get("protocol") or "tcp"
    if protocol not in PROTOCOLS:
        protocol = "tcp"
    conn = {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "host": host,
        "port": port,
        "protocol": protocol,
        "token": payload.get("token", "") or "",
        "note": payload.get("note", "") or "",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_default": False,
    }
    with _LOCK:
        conns = _read_all()
        conns.append(conn)
        _write_all(conns)
    return conn


def update_connection(conn_id, payload):
    """更新指定 id 的连接，成功返回 True。"""
    if payload is None:
        payload = {}
    with _LOCK:
        conns = _read_all()
        for c in conns:
            if c.get("id") == conn_id:
                for key in ("name", "host", "port", "protocol", "token", "note"):
                    if key in payload:
                        val = payload[key]
                        if key == "port":
                            try:
                                val = int(val)
                            except (TypeError, ValueError):
                                continue
                        if key == "protocol" and val not in PROTOCOLS:
                            continue
                        c[key] = val if val is not None else ""
                _write_all(conns)
                return True
    return False


def delete_connection(conn_id):
    """删除指定 id 的连接，成功返回 True。"""
    with _LOCK:
        conns = _read_all()
        new = [c for c in conns if c.get("id") != conn_id]
        if len(new) == len(conns):
            return False
        _write_all(new)
        return True


def set_default(conn_id):
    """将指定 id 设为默认（is_default=True），其余置为 False。成功返回 True。"""
    with _LOCK:
        conns = _read_all()
        found = False
        for c in conns:
            c["is_default"] = (c.get("id") == conn_id)
            if c["is_default"]:
                found = True
        if not found:
            return False
        _write_all(conns)
        return True
