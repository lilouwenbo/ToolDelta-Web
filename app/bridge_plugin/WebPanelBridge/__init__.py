import os
import json
import inspect
from tooldelta import Plugin, plugin_entry

class WebPanelBridge(Plugin):
    name = "WebPanelBridge"
    author = "WebPanel"
    version = (1, 0, 0)

    def __init__(self, frame):
        super().__init__(frame)
        self._command_registry = {}
        self._original_register = frame.cmd_manager.add_console_cmd_trigger
        frame.cmd_manager.add_console_cmd_trigger = self._tracked_register
        self._bridge_data_path = os.path.join(self.data_path, "commands_registry.json")
        self._load_registry()
        self.ListenFrameExit(lambda _: self._save_registry())

    def _tracked_register(self, triggers, arg_hint, usage, func):
        plugin_name = self._find_caller_plugin()
        for trigger in triggers:
            self._command_registry[trigger] = {
                "plugin": plugin_name,
                "usage": usage,
                "hint": arg_hint,
            }
        self._save_registry()
        self._original_register(triggers, arg_hint, usage, func)

    def _find_caller_plugin(self):
        for frame_info in inspect.stack():
            locals_dict = frame_info.frame.f_locals
            if "self" in locals_dict:
                obj = locals_dict["self"]
                if hasattr(obj, "name") and hasattr(obj, "frame"):
                    return obj.name
        return "未知"

    def _load_registry(self):
        if os.path.isfile(self._bridge_data_path):
            with open(self._bridge_data_path, "r", encoding="utf-8") as f:
                self._command_registry = json.load(f)

    def _save_registry(self):
        os.makedirs(os.path.dirname(self._bridge_data_path), exist_ok=True)
        with open(self._bridge_data_path, "w", encoding="utf-8") as f:
            json.dump(self._command_registry, f, ensure_ascii=False, indent=2)

entry = plugin_entry(WebPanelBridge)
