import os
import shutil
import mimetypes
from flask import Blueprint, request, jsonify, send_file, session, after_this_request
from app.log_service import log_service
from config import Config

bp = Blueprint("files", __name__, url_prefix="/api/files")

ALLOWED_ROOT = os.path.normpath(Config.TOOLDELTA_DIR)

def audit(action, detail=""):
    user = session.get("username", "?")
    ip = request.remote_addr or "?"
    log_service.info(f"[{user}@{ip}] {action} {detail}", "AUDIT")

def ok(data=None):
    r = {"success": True}
    if data is not None:
        r["data"] = data
    return jsonify(r)

def fail(msg):
    return jsonify({"success": False, "error": msg})

def safe_path(path_str):
    if not path_str:
        return ALLOWED_ROOT
    full = os.path.normpath(os.path.join(ALLOWED_ROOT, path_str.lstrip("/\\")))
    if not full.startswith(ALLOWED_ROOT):
        return None
    return full

@bp.route("/list")
def list_files():
    raw = request.args.get("path", "")
    full = safe_path(raw)
    if not full:
        return fail("路径不允许")
    if not os.path.exists(full):
        return fail("路径不存在")
    if os.path.isfile(full):
        return fail("路径不是目录")
    try:
        entries = []
        for name in sorted(os.listdir(full), key=lambda x: (not os.path.isdir(os.path.join(full, x)), x.lower())):
            path = os.path.join(full, name)
            rel = os.path.relpath(path, ALLOWED_ROOT)
            stat = os.stat(path)
            is_dir = os.path.isdir(path)
            entries.append({
                "name": name,
                "path": rel,
                "is_dir": is_dir,
                "size": 0 if is_dir else stat.st_size,
                "mtime": stat.st_mtime,
                "ext": os.path.splitext(name)[1].lower() if not is_dir else "",
            })
        return ok({"entries": entries, "current": os.path.relpath(full, ALLOWED_ROOT), "root": ALLOWED_ROOT})
    except Exception as e:
        return fail(str(e))

@bp.route("/read")
def read_file():
    raw = request.args.get("path", "")
    full = safe_path(raw)
    if not full:
        return fail("路径不允许")
    if not os.path.isfile(full):
        return fail("不是文件")
    try:
        size = os.path.getsize(full)
        if size > 5 * 1024 * 1024:
            return fail("文件超过5MB，无法在线查看")
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return ok({"content": content, "path": os.path.relpath(full, ALLOWED_ROOT), "size": size})
    except Exception as e:
        return fail(str(e))

@bp.route("/save", methods=["POST"])
def save_file():
    data = request.get_json(silent=True) or {}
    raw = (data.get("path") or "").strip()
    content = data.get("content") or ""
    full = safe_path(raw)
    if not full:
        return fail("路径不允许")
    if not full.startswith(ALLOWED_ROOT):
        return fail("路径不允许")
    try:
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        audit("保存文件", f"路径={raw}")
        return ok()
    except Exception as e:
        return fail(str(e))

@bp.route("/upload", methods=["POST"])
def upload_file():
    raw = request.form.get("path", "")
    full = safe_path(raw)
    if not full:
        return fail("路径不允许")
    if "file" not in request.files:
        return fail("未上传文件")
    f = request.files["file"]
    if not f.filename:
        return fail("文件名为空")
    dest = os.path.join(full, f.filename)
    try:
        f.save(dest)
        audit("上传文件", f"路径={os.path.join(raw, f.filename)}")
        return ok()
    except Exception as e:
        return fail(str(e))

@bp.route("/delete", methods=["POST"])
def delete_item():
    data = request.get_json(silent=True) or {}
    raw = (data.get("path") or "").strip()
    full = safe_path(raw)
    if not full:
        return fail("路径不允许")
    if full == ALLOWED_ROOT:
        return fail("不能删除根目录")
    try:
        if os.path.isdir(full):
            shutil.rmtree(full)
        else:
            os.remove(full)
        audit("删除", f"路径={raw}")
        return ok()
    except Exception as e:
        return fail(str(e))

@bp.route("/mkdir", methods=["POST"])
def make_dir():
    data = request.get_json(silent=True) or {}
    raw = (data.get("path") or "").strip()
    full = safe_path(raw)
    if not full:
        return fail("路径不允许")
    if os.path.exists(full):
        return fail("路径已存在")
    try:
        os.makedirs(full)
        audit("创建目录", f"路径={raw}")
        return ok()
    except Exception as e:
        return fail(str(e))

@bp.route("/download")
def download_file():
    raw = request.args.get("path", "")
    full = safe_path(raw)
    if not full or not os.path.isfile(full):
        return fail("文件不存在")
    return send_file(full, as_attachment=True, download_name=os.path.basename(full))

@bp.route("/rename", methods=["POST"])
def rename_item():
    data = request.get_json(silent=True) or {}
    raw = (data.get("path") or "").strip()
    new_name = (data.get("new_name") or "").strip()
    if not new_name:
        return fail("新名称为空")
    full = safe_path(raw)
    if not full or not os.path.exists(full):
        return fail("路径不存在")
    parent = os.path.dirname(full)
    dest = os.path.join(parent, new_name)
    if os.path.exists(dest):
        return fail("目标路径已存在")
    try:
        os.rename(full, dest)
        audit("重命名", f"{raw} -> {new_name}")
        return ok()
    except Exception as e:
        return fail(str(e))

@bp.route("/move", methods=["POST"])
def move_item():
    data = request.get_json(silent=True) or {}
    raw = (data.get("path") or "").strip()
    dest_raw = (data.get("destination") or "").strip()
    full = safe_path(raw)
    dest_full = safe_path(dest_raw)
    if not full or not os.path.exists(full):
        return fail("源路径不存在")
    if not dest_full:
        return fail("目标路径不允许")
    if os.path.exists(dest_full):
        return fail("目标已存在")
    try:
        os.rename(full, dest_full)
        audit("移动", f"{raw} -> {dest_raw}")
        return ok()
    except Exception as e:
        return fail(str(e))

@bp.route("/copy", methods=["POST"])
def copy_item():
    data = request.get_json(silent=True) or {}
    raw = (data.get("path") or "").strip()
    dest_raw = (data.get("destination") or "").strip()
    full = safe_path(raw)
    dest_full = safe_path(dest_raw)
    if not full or not os.path.exists(full):
        return fail("源路径不存在")
    if not dest_full:
        return fail("目标路径不允许")
    if os.path.exists(dest_full):
        return fail("目标已存在")
    try:
        if os.path.isdir(full):
            shutil.copytree(full, dest_full)
        else:
            shutil.copy2(full, dest_full)
        audit("复制", f"{raw} -> {dest_raw}")
        return ok()
    except Exception as e:
        return fail(str(e))

@bp.route("/download-dir")
def download_dir():
    raw = request.args.get("path", "")
    full = safe_path(raw)
    if not full or not os.path.isdir(full):
        return fail("目录不存在")
    import tempfile
    import zipfile
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_path = tmp.name
    tmp.close()
    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(full):
                for fn in files:
                    fp = os.path.join(root, fn)
                    arcname = os.path.relpath(fp, full)
                    zf.write(fp, arcname)
    except Exception as e:
        if os.path.isfile(tmp_path):
            os.remove(tmp_path)
        return fail(str(e))
    audit("下载目录", f"路径={raw}")

    @after_this_request
    def _cleanup(response):
        try:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return response

    return send_file(tmp_path, as_attachment=True, download_name=os.path.basename(full) + ".zip")

@bp.route("/search")
def search_files():
    raw = request.args.get("path", "")
    query = request.args.get("q", "").strip().lower()
    if not query:
        return fail("请输入搜索关键词")
    full = safe_path(raw)
    if not full or not os.path.isdir(full):
        return fail("路径不存在")
    try:
        results = []
        for root, dirs, files in os.walk(full):
            for name in files + dirs:
                if query in name.lower():
                    fp = os.path.join(root, name)
                    rel = os.path.relpath(fp, ALLOWED_ROOT)
                    stat = os.stat(fp)
                    is_dir = os.path.isdir(fp)
                    results.append({
                        "name": name,
                        "path": rel,
                        "is_dir": is_dir,
                        "size": 0 if is_dir else stat.st_size,
                        "mtime": stat.st_mtime,
                        "ext": os.path.splitext(name)[1].lower() if not is_dir else "",
                    })
        return ok({"entries": results, "current": os.path.relpath(full, ALLOWED_ROOT), "root": ALLOWED_ROOT})
    except Exception as e:
        return fail(str(e))

@bp.route("/batch-delete", methods=["POST"])
def batch_delete():
    data = request.get_json(silent=True) or {}
    paths = data.get("paths") or []
    if not paths:
        return fail("未选择文件")
    deleted = []
    errors = []
    for raw in paths:
        full = safe_path(raw.strip())
        if not full:
            errors.append(f"{raw}: 路径不允许")
            continue
        if full == ALLOWED_ROOT:
            errors.append(f"{raw}: 不能删除根目录")
            continue
        try:
            if os.path.isdir(full):
                shutil.rmtree(full)
            else:
                os.remove(full)
            deleted.append(raw)
        except Exception as e:
            errors.append(f"{raw}: {e}")
    if deleted:
        audit("批量删除", str(deleted))
    return ok({"deleted": deleted, "errors": errors})
