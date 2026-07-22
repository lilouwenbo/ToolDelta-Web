import os
import sys
import re
import subprocess
import threading
import time
import locale
import shutil
import zipfile
from flask import current_app
from app.log_service import log_service

_MC_COLOR_RE = re.compile(r"§[0-9a-fklmnor]")
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
_ANSI_SEQ_RE = re.compile(r"\x1b\[([0-9;]*)m")
# 匹配除 SGR 颜色序列(\x1b[...m)之外的所有 ANSI 控制序列(清屏/清行/光标移动等)，
# 避免在控制台中渲染出乱码控制字符。排除 m/M 结尾以保留颜色序列供后续转换。
_ANSI_NON_COLOR_RE = re.compile(r"\x1b\[[0-9;?]*[a-ln-zA-Z]")
# 剥离"非 CSI"的终端控制序列：OSC(\x1b]...title...\x07/ST)、字符集/私有模式
# (\x1b(0 等行绘制字符集)、以及任何孤立 ESC。这些序列在 Web 终端里无法渲染，
# 若不清理会以裸控制字符(乱码)形式残留，表现为"终端字符转义失效"。
# 负向先行 (?![\[]) 保证不误伤 CSI(\x1b[...，含颜色 SGR) 序列。
_ANSI_NON_CSI_RE = re.compile(
    r"\x1b\][^\x07\x1b]*?(?:\x07|\x1b\\)"   # OSC: \x1b]...BEL/ST
    r"|\x1b[\(\)\*\+\-\.\/][^\x1b]?"        # 字符集/私有模式: \x1b(0 等
    r"|\x1b(?![\[])"                         # 兜底: 孤立 ESC(排除 CSI)
)

_ANSI_COLORS = {
    "0;30": "#000", "0;31": "#e74c3c", "0;32": "#2ecc71", "0;33": "#f1c40f",
    "0;34": "#3498db", "0;35": "#9b59b6", "0;36": "#1abc9c", "0;37": "#ecf0f1",
    "1;30": "#555", "1;31": "#ff6b6b", "1;32": "#55efc4", "1;33": "#ffeaa7",
    "1;34": "#74b9ff", "1;35": "#a29bfe", "1;36": "#00cec9", "1;37": "#fff",
    "0;90": "#666", "0;91": "#e17055", "0;92": "#00b894", "0;93": "#fdcb6e",
    "0;94": "#6c5ce7", "0;95": "#e056fd", "0;96": "#00cec9", "0;97": "#dfe6e9",
    "1;90": "#999", "1;91": "#fab1a0", "1;92": "#55efc4", "1;93": "#ffeaa7",
    "1;94": "#a29bfe", "1;95": "#fd79a8", "1;96": "#81ecec", "1;97": "#fff",
}

def strip_ansi(text):
    text = _MC_COLOR_RE.sub("", text)
    text = _ANSI_ESCAPE_RE.sub("", text)
    text = _ANSI_NON_CSI_RE.sub("", text)
    return text

def ansi_to_html(text):
    text = _MC_COLOR_RE.sub("", text)
    # 先剥离 OSC/字符集/孤立 ESC(非 CSI 控制序列)，避免裸控制字符残留成乱码；
    # 再剥离 CSI 非颜色序列，保留 SGR(\x1b[...m) 供下方颜色转换。
    text = _ANSI_NON_CSI_RE.sub("", text)
    text = _ANSI_NON_COLOR_RE.sub("", text)
    parts = _ANSI_SEQ_RE.split(text)
    html = ""
    reset = True
    fg = None
    bold = False
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part:
                if reset:
                    html += "<span>" if fg else ""
                    html += escape_html(part)
                    if fg:
                        html += "</span>"
                    else:
                        html = html.replace("<span>", "", 1) if html.endswith("<span>") else html
                else:
                    style = ""
                    if bold:
                        style += "font-weight:bold;"
                    if fg:
                        style += "color:" + fg + ";"
                    if style:
                        html += '<span style="' + style + '">' + escape_html(part) + "</span>"
                    else:
                        html += escape_html(part)
        else:
            codes = part.split(";")
            reset = True
            fg = None
            bold = False
            for code in codes:
                if not code:
                    continue
                if code == "0":
                    reset = True
                    fg = None
                    bold = False
                elif code == "1":
                    bold = True
                    reset = False
                elif code in ("22", "21"):
                    bold = False
                elif code in ("39", "49"):
                    fg = None
                else:
                    key = None
                    if code in _ANSI_COLORS:
                        key = code
                    for k in _ANSI_COLORS:
                        if k.endswith(";" + code) or k.startswith(code + ";"):
                            if bold and not k.startswith("1;"):
                                key = "1;" + code if k == "0;" + code else k
                            else:
                                key = k
                            break
                    if key and key in _ANSI_COLORS:
                        fg = _ANSI_COLORS[key]
                        reset = False
    return html

def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def detect_encoding(raw_bytes):
    encodings = ["utf-8", locale.getpreferredencoding(), "gbk", "gb2312"]
    for enc in encodings:
        try:
            raw_bytes.decode(enc, errors="strict")
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    return "utf-8"

class ToolDeltaManager:
    def __init__(self):
        self.process = None
        self.output_thread = None
        self.running = False
        self.listeners = []
        self._lock = threading.Lock()
        self.output_buffer = []
        self.output_raw_buffer = []
        self.MAX_BUFFER = 500

    def init_app(self, app):
        self.app = app

    def _is_valid_main(self, main_py):
        """检查 main.py 是否真正可用：存在、非空、且语法可编译（仅编译不执行，避免副作用）。

        这样即使 main.py 被意外清空/损坏（仅 isfile 为 True），也能被识别为无效，
        从而触发自动重新解压出厂包恢复，而不是带着坏文件去启动导致控制台起不来。
        """
        if not os.path.isfile(main_py):
            return False
        try:
            if os.path.getsize(main_py) == 0:
                return False
            import ast
            with open(main_py, "r", encoding="utf-8", errors="replace") as f:
                ast.parse(f.read())
            return True
        except Exception:
            return False

    def _ensure_main_program(self):
        """确保主程序存在：首次启动且 TOOLDELTA_DIR 为空（没有 main.py）时，
        自动从出厂包(TOOLDELTA_SOURCE_ZIP)解压初始主程序到 TOOLDELTA_DIR。
        返回 (ok, msg)。
        """
        app = self.app
        td_dir = app.config["TOOLDELTA_DIR"]
        main_py = app.config["TOOLDELTA_MAIN"]
        if self._is_valid_main(main_py):
            return True, "主程序已存在"
        zip_path = app.config.get("TOOLDELTA_SOURCE_ZIP")
        if not zip_path or not os.path.isfile(zip_path):
            return False, "出厂程序包不存在: " + (zip_path or "未配置")
        try:
            with zipfile.ZipFile(zip_path) as z:
                names = z.namelist()
            # 出厂包通常带统一顶层目录(如 ToolDelta-main/)，解压时剥离，
            # 确保 main.py 落在 TOOLDELTA_DIR 下，避免出现嵌套目录。
            top = ""
            if names and "/" in names[0]:
                top = names[0].split("/", 1)[0] + "/"
            os.makedirs(td_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path) as z:
                for info in z.infolist():
                    rel = info.filename[len(top):] if (top and info.filename.startswith(top)) else info.filename
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
            if not self._is_valid_main(main_py):
                return False, "解压完成但 main.py 未生成或无效，请检查出厂包"
            return True, "已从出厂包解压主程序"
        except Exception as e:
            return False, f"解压出厂包失败: {e}"

    def start(self):
        with self._lock:
            if self.running:
                return True
            if not getattr(self, "app", None):
                self._broadcast("system", "应用上下文未初始化，无法启动")
                return False
            main_py = self.app.config["TOOLDELTA_MAIN"]
            td_dir = self.app.config["TOOLDELTA_DIR"]
            if not os.path.isfile(main_py):
                # 首次启动/初始化时 TOOLDELTA_DIR 可能为空，自动解压出厂包让主程序就绪
                ok, msg = self._ensure_main_program()
                if not ok:
                    self._broadcast("system", "找不到 " + main_py + "（" + msg + "）")
                    return False
                self._broadcast("system", msg)
            try:
                startupinfo = None
                if os.name == "nt":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                self.process = subprocess.Popen(
                    [sys.executable, main_py, "-l", "1"],
                    cwd=td_dir,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    startupinfo=startupinfo,
                    bufsize=0,
                    env=env,
                )
                self.running = True
                self._broadcast("system", "ToolDelta 进程已启动")
                self.output_thread = threading.Thread(target=self._read_output, daemon=True)
                self.output_thread.start()
                return True
            except Exception as e:
                self._broadcast("system", "启动失败: " + str(e))
                return False

    def stop(self):
        with self._lock:
            if not self.running or not self.process:
                return True
            try:
                if self.process.stdin:
                    self.process.stdin.close()
            except:
                pass
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass
            self.running = False
            self.process = None
            self._broadcast("system", "ToolDelta 进程已停止")
            return True

    def restart(self):
        self.stop()
        time.sleep(1)
        return self.start()

    def send_command(self, cmd):
        with self._lock:
            if self.running and self.process and self.process.stdin:
                try:
                    self.process.stdin.write((cmd + "\n").encode("utf-8", errors="replace"))
                    self.process.stdin.flush()
                    return True
                except:
                    return False
        return False

    def _read_output(self):
        encoding = "utf-8"
        detected = False
        while self.running and self.process:
            try:
                raw = self.process.stdout.readline()
                if not raw:
                    break
                if not detected:
                    # 先尝试 utf-8 实时显示；遇到非 utf-8 字节再检测编码，
                    # 兼顾实时性与中文(gbk等)正确解码，避免控制台开头乱码
                    try:
                        line = raw.decode("utf-8").rstrip("\r\n")
                    except UnicodeDecodeError:
                        encoding = detect_encoding(raw)
                        detected = True
                        line = raw.decode(encoding, errors="replace").rstrip("\r\n")
                else:
                    line = raw.decode(encoding, errors="replace").rstrip("\r\n")
                self._emit_line(line)
            except:
                break
        with self._lock:
            self.running = False
            self._broadcast("system", "ToolDelta 进程已退出")

    def _emit_line(self, line):
        cleaned = strip_ansi(line)
        self.output_raw_buffer.append(line)
        self.output_buffer.append(cleaned)
        if len(self.output_buffer) > self.MAX_BUFFER:
            self.output_buffer = self.output_buffer[-self.MAX_BUFFER:]
            self.output_raw_buffer = self.output_raw_buffer[-self.MAX_BUFFER:]
        log_service.info("[ToolDelta] " + cleaned)
        self._broadcast("output", line)

    def get_status(self):
        with self._lock:
            alive = False
            if self.process:
                alive = self.process.poll() is None
            return {
                "running": self.running and alive,
                "pid": self.process.pid if self.process else None,
                "buffer_size": len(self.output_buffer),
            }

    def get_output(self, tail=200, as_html=False):
        if as_html:
            return [ansi_to_html(l) for l in self.output_raw_buffer[-tail:]]
        return self.output_raw_buffer[-tail:]

    def clear_listeners(self):
        self.listeners = []

    def add_listener(self, cb):
        if cb not in self.listeners:
            self.listeners.append(cb)

    def _broadcast(self, type_, data):
        for cb in self.listeners:
            try:
                cb(type_, data)
            except:
                pass

tooldelta_manager = ToolDeltaManager()
