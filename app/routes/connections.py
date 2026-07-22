from flask import Blueprint, render_template, request, jsonify

from app import connection_service as conn_svc

bp = Blueprint("connections", __name__)


def _ok(data=None):
    r = {"success": True}
    if data is not None:
        r["data"] = data
    return jsonify(r)


def _fail(msg):
    return jsonify({"success": False, "error": msg})


@bp.route("/connections")
def connections_page():
    return render_template("connections.html")


@bp.route("/api/connections")
def api_list():
    return jsonify(conn_svc.list_connections())


@bp.route("/api/connections/add", methods=["POST"])
def api_add():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    host = (data.get("host") or "").strip()
    port = data.get("port")
    if not name:
        return _fail("名称不能为空")
    if not host:
        return _fail("地址不能为空")
    try:
        port = int(port)
    except (TypeError, ValueError):
        return _fail("端口必须为数字")
    conn = conn_svc.add_connection({
        "name": name,
        "host": host,
        "port": port,
        "protocol": data.get("protocol"),
        "token": data.get("token"),
        "note": data.get("note"),
    })
    return jsonify({"success": True, "conn": conn})


@bp.route("/api/connections/update", methods=["POST"])
def api_update():
    data = request.get_json(silent=True) or {}
    conn_id = data.get("id")
    if not conn_id:
        return _fail("缺少 id")
    if "port" in data and data["port"] not in (None, ""):
        try:
            int(data["port"])
        except (TypeError, ValueError):
            return _fail("端口必须为数字")
    ok = conn_svc.update_connection(conn_id, data)
    if not ok:
        return _fail("连接不存在")
    return _ok()


@bp.route("/api/connections/delete", methods=["POST"])
def api_delete():
    data = request.get_json(silent=True) or {}
    conn_id = data.get("id")
    if not conn_id:
        return _fail("缺少 id")
    ok = conn_svc.delete_connection(conn_id)
    if not ok:
        return _fail("连接不存在")
    return _ok()


@bp.route("/api/connections/default", methods=["POST"])
def api_default():
    data = request.get_json(silent=True) or {}
    conn_id = data.get("id")
    if not conn_id:
        return _fail("缺少 id")
    ok = conn_svc.set_default(conn_id)
    if not ok:
        return _fail("连接不存在")
    return _ok()
