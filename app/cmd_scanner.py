import os
import ast
import json
from flask import current_app

class CommandScanner:
    def scan_plugin(self, plugin_dir, plugin_name):
        init_py = os.path.join(plugin_dir, "__init__.py")
        if not os.path.isfile(init_py):
            return []
        with open(init_py, "r", encoding="utf-8", errors="replace") as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError:
                return []
        commands = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "add_console_cmd_trigger"):
                continue
            args = node.args
            if len(args) < 3:
                continue
            try:
                triggers = self._safe_literal_eval(args[0])
                if not isinstance(triggers, list):
                    continue
                hint = self._safe_literal_eval(args[1]) if len(args) > 1 else None
                usage = self._safe_literal_eval(args[2]) if len(args) > 2 else ""
                commands.append({
                    "triggers": triggers,
                    "hint": hint if isinstance(hint, str) else None,
                    "usage": usage if isinstance(usage, str) else "",
                })
            except:
                continue
        return commands

    def scan_all_plugins(self):
        pdir = current_app.config["TOOLDELTA_CLASSIC_PLUGIN_PATH"]
        result = []
        if os.path.isdir(pdir):
            for d in sorted(os.listdir(pdir)):
                full = os.path.join(pdir, d)
                if not os.path.isdir(full):
                    continue
                name = d.replace("+disabled", "")
                commands = self.scan_plugin(full, name)
                if commands:
                    result.append({
                        "plugin": name,
                        "is_enabled": not d.endswith("+disabled"),
                        "commands": commands,
                        "count": len(commands),
                    })
        # 合并 WebPanelBridge 运行时注册的命令：静态 AST 扫描无法覆盖
        # 运行时才 add_console_cmd_trigger 的动态命令，bridge 会在 ToolDelta
        # 端把它们记录到插件数据目录的 commands_registry.json，这里并入，
        # 使命令库 = 静态扫描 + 运行时注册，供命令页/控制台补全共用。
        registry = self._load_bridge_registry()
        if registry:
            by_plugin = {e["plugin"]: e for e in result}
            for trigger, info in registry.items():
                if not isinstance(info, dict):
                    continue
                pname = info.get("plugin") or "未知"
                entry = by_plugin.get(pname)
                if not entry:
                    entry = {"plugin": pname, "is_enabled": True, "commands": [], "count": 0}
                    result.append(entry)
                    by_plugin[pname] = entry
                if any(trigger in c["triggers"] for c in entry["commands"]):
                    continue
                entry["commands"].append({
                    "triggers": [trigger],
                    "hint": info.get("hint") if isinstance(info.get("hint"), str) else None,
                    "usage": info.get("usage", "") if isinstance(info.get("usage"), str) else "",
                })
            for e in result:
                e["count"] = len(e["commands"])
        return result

    def _load_bridge_registry(self):
        """读取 WebPanelBridge 运行时记录到插件数据目录的命令注册表(容错)。"""
        try:
            base = current_app.config.get("TOOLDELTA_PLUGIN_DATA_DIR")
            if not base:
                return {}
            path = os.path.join(base, "WebPanelBridge", "commands_registry.json")
            if not os.path.isfile(path):
                return {}
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data or {}
        except Exception:
            return {}

    def scan_by_plugin(self, plugin_name):
        pdir = current_app.config["TOOLDELTA_CLASSIC_PLUGIN_PATH"]
        for d in [plugin_name, plugin_name + "+disabled"]:
            full = os.path.join(pdir, d)
            if os.path.isdir(full):
                commands = self.scan_plugin(full, plugin_name)
                return {
                    "plugin": plugin_name,
                    "is_enabled": not d.endswith("+disabled"),
                    "commands": commands,
                    "count": len(commands),
                }
        return None

    def _safe_literal_eval(self, node):
        try:
            return ast.literal_eval(node)
        except:
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.List):
                return [self._safe_literal_eval(e) for e in node.elts]
            raise

cmd_scanner = CommandScanner()
