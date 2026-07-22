import os
import re
from datetime import datetime

class LogService:
    def __init__(self):
        self._logs_dir = None
        self._today = None
        self._today_lines = []
        self._lock = None
        import threading
        self._lock = threading.RLock()

    def init_app(self, app):
        self._logs_dir = os.path.join(app.instance_path, "logs")
        os.makedirs(self._logs_dir, exist_ok=True)
        self._rotate()

    def _rotate(self):
        with self._lock:
            today = datetime.now().strftime("%Y-%m-%d")
            if today != self._today:
                self._today = today
                self._today_lines = []
                self._load_today()

    def _load_today(self):
        path = self._today_path()
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                self._today_lines = [l.rstrip("\r\n") for l in f.readlines()]

    def _today_path(self):
        return os.path.join(self._logs_dir, self._today + ".log") if self._logs_dir else None

    def _write(self, level, source, message):
        self._rotate()
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}][{level}][{source}] {message}"
        with self._lock:
            self._today_lines.append(line)
            path = self._today_path()
            if path:
                try:
                    with open(path, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                except:
                    pass

    def info(self, message, source="SYSTEM"):
        self._write("INFO", source, message)

    def warn(self, message, source="SYSTEM"):
        self._write("WARN", source, message)

    def error(self, message, source="SYSTEM"):
        self._write("ERROR", source, message)

    def get_today_logs(self, tail=500):
        self._rotate()
        with self._lock:
            return self._today_lines[-tail:]

    def list_log_files(self):
        self._rotate()
        if not self._logs_dir or not os.path.isdir(self._logs_dir):
            return []
        files = []
        for f in sorted(os.listdir(self._logs_dir), reverse=True):
            if f.endswith(".log"):
                path = os.path.join(self._logs_dir, f)
                size = os.path.getsize(path)
                files.append({
                    "name": f.replace(".log", ""),
                    "date": f.replace(".log", ""),
                    "size": size,
                })
        return files

    def get_log_file(self, date_str):
        path = os.path.join(self._logs_dir, date_str + ".log") if self._logs_dir else None
        if path and os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return [l.rstrip("\r\n") for l in f.readlines()]
        return []

    # ─── 日志增强：分级 / 搜索 / 过滤 / 导出 ─────────────

    LEVELS = ["INFO", "WARN", "ERROR"]

    @staticmethod
    def _parse_line(line):
        """解析单行日志，返回 dict 或 None。"""
        m = re.match(r"^\[(\d{2}:\d{2}:\d{2})\]\[(\w+)\]\[([^\]]+)\]\s*(.*)$", line)
        if not m:
            return None
        return {
            "time": m.group(1),
            "level": m.group(2),
            "source": m.group(3),
            "message": m.group(4),
        }

    def query(self, level=None, source=None, keyword=None, date=None, limit=500):
        """按级别 / 来源 / 关键字 / 日期过滤日志，返回最后 limit 条（保持原顺序）。"""
        if date is None or date == self._today:
            lines = self._today_lines
        else:
            lines = self.get_log_file(date)
        results = []
        for raw in lines:
            parsed = self._parse_line(raw)
            if not parsed:
                continue
            if level and parsed["level"].lower() != level.lower():
                continue
            if source and parsed["source"] != source:
                continue
            if keyword and keyword.lower() not in parsed["message"].lower():
                continue
            results.append(parsed)
        if limit is not None:
            results = results[-limit:]
        return results

    def list_sources(self, date=None):
        """返回某日日志中出现过的全部来源（去重并排序）。"""
        if date is None or date == self._today:
            lines = self._today_lines
        else:
            lines = self.get_log_file(date)
        sources = set()
        for raw in lines:
            parsed = self._parse_line(raw)
            if parsed:
                sources.add(parsed["source"])
        return sorted(sources)

    def export_text(self, date=None, level=None, source=None, keyword=None):
        """将过滤后的日志拼成纯文本，每行 '时间 [LEVEL][SOURCE] message'。"""
        results = self.query(level=level, source=source, keyword=keyword, date=date)
        return "\n".join(
            f"{r['time']} [{r['level']}][{r['source']}] {r['message']}" for r in results
        )


log_service = LogService()
