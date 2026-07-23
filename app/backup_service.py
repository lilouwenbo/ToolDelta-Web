import os
import json
import shutil
import zipfile
from datetime import datetime
from flask import current_app

def _parse_time(s):
    try:
        return datetime.strptime(s, "%Y%m%d_%H%M%S")
    except Exception:
        return datetime.min

class BackupService:
    def __init__(self):
        pass

    def get_backup_dir(self):
        return current_app.config["BACKUP_DIR"]

    def create_backup(self, name=None):
        td_dir = current_app.config["TOOLDELTA_DIR"]
        backup_dir = self.get_backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        label = name or f"backup_{ts}"
        zip_name = f"{label}.zip"
        zip_path = os.path.join(backup_dir, zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for folder in ["插件文件", "插件配置文件", "插件数据文件"]:
                src = os.path.join(td_dir, folder)
                if os.path.isdir(src):
                    for root, dirs, files in os.walk(src):
                        for f in files:
                            fp = os.path.join(root, f)
                            arcname = os.path.relpath(fp, td_dir)
                            z.write(fp, arcname)
            cfg_file = os.path.join(td_dir, "ToolDelta基本配置.json")
            if os.path.isfile(cfg_file):
                z.write(cfg_file, "ToolDelta基本配置.json")
        meta = {
            "name": label,
            "time": ts,
            "zip": zip_name,
            "size": os.path.getsize(zip_path),
        }
        metapath = os.path.join(backup_dir, f"{label}.meta.json")
        with open(metapath, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
        return meta

    def list_backups(self):
        backup_dir = self.get_backup_dir()
        if not os.path.isdir(backup_dir):
            return []
        backups = []
        seen = set()
        for fn in os.listdir(backup_dir):
            if fn.startswith("__"):
                continue
            if fn.endswith(".meta.json"):
                metapath = os.path.join(backup_dir, fn)
                with open(metapath, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                backups.append(meta)
                seen.add(meta["zip"])
            elif fn.endswith(".zip") and fn not in seen:
                zip_path = os.path.join(backup_dir, fn)
                backups.append({
                    "name": fn.replace(".zip", ""),
                    "time": fn.replace("backup_", "").replace(".zip", ""),
                    "zip": fn,
                    "size": os.path.getsize(zip_path),
                })
        backups.sort(key=lambda x: _parse_time(x.get("time", "")), reverse=True)
        return backups

    def restore_backup(self, zip_name):
        backup_dir = self.get_backup_dir()
        # 先停止 ToolDelta 进程，避免运行期覆盖文件导致主程序损坏（P1-3）
        try:
            from app.tooldelta_manager import tooldelta_manager
            tooldelta_manager.stop()
        except Exception:
            pass
        td_dir = current_app.config["TOOLDELTA_DIR"]
        zip_path = os.path.join(backup_dir, zip_name)
        if not os.path.isfile(zip_path):
            return False, "备份文件不存在"

        # 恢复前先对当前状态做快照，便于失败回滚
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = os.path.join(backup_dir, f"__pre_restore_{ts}.zip")

        def _make_snapshot():
            with zipfile.ZipFile(snapshot_path, "w", zipfile.ZIP_DEFLATED) as z:
                for folder in ["插件文件", "插件配置文件", "插件数据文件"]:
                    src = os.path.join(td_dir, folder)
                    if os.path.isdir(src):
                        for root, dirs, files in os.walk(src):
                            for f in files:
                                fp = os.path.join(root, f)
                                z.write(fp, os.path.relpath(fp, td_dir))
                cfg_file = os.path.join(td_dir, "ToolDelta基本配置.json")
                if os.path.isfile(cfg_file):
                    z.write(cfg_file, "ToolDelta基本配置.json")

        _make_snapshot()

        temp = os.path.join(backup_dir, "__restore_temp__")
        if os.path.isdir(temp):
            shutil.rmtree(temp)
        os.makedirs(temp, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(temp)
            for item in os.listdir(temp):
                src = os.path.join(temp, item)
                dst = os.path.join(td_dir, item)
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                elif os.path.isfile(dst):
                    os.remove(dst)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            return True, "恢复成功"
        except Exception as e:
            # 恢复失败，用快照回滚到恢复前状态
            try:
                with zipfile.ZipFile(snapshot_path, "r") as z:
                    z.extractall(td_dir)
            except Exception:
                pass
            return False, f"恢复失败，已回滚至恢复前状态: {e}"
        finally:
            if os.path.isdir(temp):
                shutil.rmtree(temp)
            if os.path.isfile(snapshot_path):
                os.remove(snapshot_path)

    def reset_to_factory(self):
        """重置 ToolDelta 到出厂状态：主程序与用户数据一并重置。

        流程：先清空整个 TOOLDELTA_DIR（删除原有主程序及用户插件/配置/数据），
        再解压出厂包（ToolDelta-main.zip）恢复主程序。
        - 出厂包顶层若有统一目录（如 ToolDelta-main/），解压时自动剥离，
          确保 main.py 落在 TOOLDELTA_DIR 下，而不会出现 TOOLDELTA_DIR/ToolDelta-main/ 的嵌套。
        """
        td_dir = current_app.config["TOOLDELTA_DIR"]
        # 先停止 ToolDelta 进程，避免运行期删文件破坏数据（P1-3）
        try:
            from app.tooldelta_manager import tooldelta_manager
            tooldelta_manager.stop()
        except Exception:
            pass
        zip_path = current_app.config.get("TOOLDELTA_SOURCE_ZIP")
        if not zip_path or not os.path.isfile(zip_path):
            return False, "出厂程序包不存在，无法进行重置"

        # 读取 zip 条目，确定顶层目录前缀（如 "ToolDelta-main/"）
        try:
            with zipfile.ZipFile(zip_path) as z:
                names = z.namelist()
        except Exception as e:
            return False, f"出厂程序包读取失败: {e}"

        top = ""
        if names and "/" in names[0]:
            top = names[0].split("/", 1)[0] + "/"

        # 1) 清空整个 TOOLDELTA_DIR（主程序与用户数据一并重置为出厂状态）
        if os.path.isdir(td_dir):
            for entry in os.listdir(td_dir):
                p = os.path.join(td_dir, entry)
                try:
                    if os.path.isdir(p) and not os.path.islink(p):
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        os.remove(p)
                except OSError:
                    pass
        os.makedirs(td_dir, exist_ok=True)

        # 2) 解压出厂包到 TOOLDELTA_DIR（去除顶层目录前缀）
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                rel = info.filename[len(top):] if top and info.filename.startswith(top) else info.filename
                if not rel:
                    continue
                dest = os.path.join(td_dir, rel)
                if info.filename.endswith("/"):
                    os.makedirs(dest, exist_ok=True)
                else:
                    parent = os.path.dirname(dest)
                    if parent:
                        os.makedirs(parent, exist_ok=True)
                    with z.open(info) as src, open(dest, "wb") as dst:
                        shutil.copyfileobj(src, dst)

        main_py = os.path.join(td_dir, "main.py")
        if not os.path.isfile(main_py):
            return False, "重置完成但 main.py 未生成，请检查出厂包"
        return True, "已恢复出厂（主程序与用户数据已重置）"

    def delete_backup(self, zip_name):
        backup_dir = self.get_backup_dir()
        zip_path = os.path.join(backup_dir, zip_name)
        meta_path = os.path.join(backup_dir, zip_name.replace(".zip", ".meta.json"))
        for p in [zip_path, meta_path]:
            if os.path.isfile(p):
                os.remove(p)
        return True

backup_service = BackupService()
