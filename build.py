# -*- coding: utf-8 -*-
"""ToolDelta-Web 构建与存档脚本。

每次执行都会：
  1. 将当前项目打成一个发布 zip（排除运行时数据 / 版本控制 / 缓存等）。
  2. 把该 zip 存入 archives/ 目录，文件名带 版本+时间戳+git短哈希，
     实现「每次构建都进行存档」，便于回溯任意历史构建。
  3. 同步更新仓库根目录的 ToolDelta-Web.zip 作为「最新交付物」。
  4. 在 archives/manifest.json 追加一条构建记录（版本/时间/git哈希/sha256/大小）。

用法:
    python3 build.py
可选环境变量:
    BUILD_VERSION  覆盖版本号(默认读 VERSION 文件)
    SKIP_LATEST    设为 1 时不覆盖根目录 ToolDelta-Web.zip
"""
import os
import sys
import json
import time
import hashlib
import subprocess
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
ARCHIVES_DIR = os.path.join(ROOT, "archives")
LATEST_ZIP = os.path.join(ROOT, "ToolDelta-Web.zip")
MANIFEST = os.path.join(ARCHIVES_DIR, "manifest.json")

# 打包时需要排除的项（运行时数据 / 版本控制 / 缓存 / 历史构建产物）
EXCLUDE_DIRS = {
    ".git", "__pycache__", "backups", "ToolDelta", "plugin_market",
    "instance", "archives", "build", "dist", ".venv", "venv", "env",
}
EXCLUDE_FILES = {
    "ToolDelta-Web.zip",  # 旧的「最新交付物」不要打回包里
    "selfcheck_summary.txt",  # 自检结果产物不进包
}
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".log", ".db", ".sqlite3")


def get_version():
    if os.environ.get("BUILD_VERSION"):
        return os.environ["BUILD_VERSION"].strip()
    vf = os.path.join(ROOT, "VERSION")
    if os.path.isfile(vf):
        with open(vf, encoding="utf-8") as f:
            v = f.read().strip()
            if v:
                return v
    return "dev"


def get_git_hash():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return "nogit"


def should_exclude(path):
    # path 相对 ROOT
    parts = path.split(os.sep)
    for p in parts:
        if p in EXCLUDE_DIRS:
            return True
    name = parts[-1]
    if name in EXCLUDE_FILES:
        return True
    if name.lower().endswith(EXCLUDE_SUFFIXES):
        return True
    return False


def collect_files():
    result = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = os.path.relpath(dirpath, ROOT)
        # 剪枝：整目录排除
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            rel = os.path.normpath(os.path.join(rel_dir, fn)) if rel_dir != "." else fn
            if rel == "." or should_exclude(rel):
                continue
            result.append(rel)
    result.sort()
    return result


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    version = get_version()
    git_hash = get_git_hash()
    ts = time.strftime("%Y%m%d-%H%M%S")
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")

    os.makedirs(ARCHIVES_DIR, exist_ok=True)
    files = collect_files()
    if not files:
        print("未收集到任何文件，构建中止")
        sys.exit(1)

    archive_name = "ToolDelta-Web_%s_%s_%s.zip" % (version, ts, git_hash)
    archive_path = os.path.join(ARCHIVES_DIR, archive_name)

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            z.write(os.path.join(ROOT, rel), rel)
    size = os.path.getsize(archive_path)
    digest = sha256_of(archive_path)
    print("已打包 %d 个文件 -> %s (%d 字节)" % (len(files), archive_name, size))

    # 同步最新交付物
    if os.environ.get("SKIP_LATEST") != "1":
        import shutil
        shutil.copyfile(archive_path, LATEST_ZIP)
        print("已更新最新交付物: ToolDelta-Web.zip")

    # 写 manifest
    record = {
        "version": version,
        "built_at": stamp,
        "git": git_hash,
        "file": archive_name,
        "size": size,
        "sha256": digest,
        "files": len(files),
    }
    manifest = []
    if os.path.isfile(MANIFEST):
        try:
            with open(MANIFEST, encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = []
    manifest.append(record)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("已记录构建档案到 archives/manifest.json")

    print("\n构建摘要:")
    print("  版本   :", version)
    print("  时间   :", stamp)
    print("  git    :", git_hash)
    print("  文件数 :", len(files))
    print("  sha256 :", digest)
    print("  存档   :", archive_path)


if __name__ == "__main__":
    main()
