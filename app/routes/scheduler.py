from flask import Blueprint, render_template, request, jsonify

from app.scheduler_service import scheduler_service

bp = Blueprint("scheduler", __name__)


@bp.route("/scheduler")
def scheduler_page():
    return render_template("scheduler.html")


@bp.route("/api/scheduler/jobs", methods=["GET"])
def api_jobs():
    return jsonify(scheduler_service.list_jobs())


@bp.route("/api/scheduler/add", methods=["POST"])
def api_add():
    payload = request.get_json(silent=True) or {}
    try:
        job = scheduler_service.add_job(payload)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})
    except Exception:
        return jsonify({"success": False, "message": "添加任务失败"})
    return jsonify({"success": True, "job": job})


@bp.route("/api/scheduler/update", methods=["POST"])
def api_update():
    payload = request.get_json(silent=True) or {}
    job_id = payload.get("id")
    if not job_id:
        return jsonify({"success": False, "message": "缺少任务 id"})
    try:
        ok = scheduler_service.update_job(job_id, payload)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})
    except Exception:
        return jsonify({"success": False, "message": "更新任务失败"})
    if not ok:
        return jsonify({"success": False, "message": "任务不存在"})
    return jsonify({"success": True})


@bp.route("/api/scheduler/delete", methods=["POST"])
def api_delete():
    payload = request.get_json(silent=True) or {}
    job_id = payload.get("id")
    if not job_id:
        return jsonify({"success": False, "message": "缺少任务 id"})
    ok = scheduler_service.delete_job(job_id)
    if not ok:
        return jsonify({"success": False, "message": "任务不存在"})
    return jsonify({"success": True})


@bp.route("/api/scheduler/run", methods=["POST"])
def api_run():
    payload = request.get_json(silent=True) or {}
    job_id = payload.get("id")
    if not job_id:
        return jsonify({"success": False, "message": "缺少任务 id"})
    ok = scheduler_service.run_now(job_id)
    if not ok:
        return jsonify({"success": False, "message": "任务不存在"})
    return jsonify({"success": True})
