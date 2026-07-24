from flask import Blueprint, render_template, request, jsonify

from app.watchdog_service import watchdog_service

bp = Blueprint("watchdog", __name__)


@bp.route("/watchdog")
def watchdog_page():
    return render_template("watchdog.html")


@bp.route("/api/watchdog/config", methods=["GET"])
def watchdog_config():
    return jsonify(watchdog_service.get_config())


@bp.route("/api/watchdog/set", methods=["POST"])
def watchdog_set():
    payload = request.get_json(silent=True) or {}
    ok = watchdog_service.set_config(payload)
    return jsonify({"success": ok})


@bp.route("/api/watchdog/status", methods=["GET"])
def watchdog_status():
    return jsonify(watchdog_service.get_runtime())


@bp.route("/api/watchdog/enable", methods=["POST"])
def watchdog_enable():
    watchdog_service.enable()
    return jsonify({"success": True})


@bp.route("/api/watchdog/disable", methods=["POST"])
def watchdog_disable():
    watchdog_service.disable()
    return jsonify({"success": True})
