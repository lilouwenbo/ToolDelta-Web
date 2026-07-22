from flask import Blueprint, render_template, request, jsonify, Response

from app.log_service import log_service

bp = Blueprint("logs", __name__)

@bp.route("/logs")
def logs_page():
    return render_template("logs.html")

# ─── 日志增强 API ──────────────────────────────

@bp.route("/api/logs/query")
def api_logs_query():
    date = request.args.get("date") or None
    level = request.args.get("level") or None
    source = request.args.get("source") or None
    keyword = request.args.get("keyword") or None
    limit = request.args.get("limit", 500, type=int)
    lines = log_service.query(level=level, source=source, keyword=keyword, date=date, limit=limit)
    sources = log_service.list_sources(date)
    return jsonify({"lines": lines, "sources": sources})


@bp.route("/api/logs/sources")
def api_logs_sources():
    date = request.args.get("date") or None
    return jsonify(log_service.list_sources(date))


@bp.route("/api/logs/export")
def api_logs_export():
    date = request.args.get("date") or None
    level = request.args.get("level") or None
    source = request.args.get("source") or None
    keyword = request.args.get("keyword") or None
    text = log_service.export_text(date=date, level=level, source=source, keyword=keyword)
    return Response(
        text,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=logs_export.txt"},
    )
