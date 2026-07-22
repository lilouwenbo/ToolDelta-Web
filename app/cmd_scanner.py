import os
import ast
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
        if not os.path.isdir(pdir):
            return []
        result = []
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
        return result

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
