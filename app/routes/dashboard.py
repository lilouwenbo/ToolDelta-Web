from flask import Blueprint, jsonify

from app.dashboard_service import dashboard_service

bp = Blueprint("dashboard", __name__)


@bp.route("/api/dashboard", methods=["GET"])
def dashboard():
    """聚合状态仪表盘数据，返回 JSON。"""
    return jsonify(dashboard_service.get_dashboard())


@bp.route("/api/version", methods=["GET"])
def version():
    """返回 Web 面板 / ToolDelta / 构建哈希 三版本信息（P2-5）。"""
    return jsonify(dashboard_service.get_version_info())
