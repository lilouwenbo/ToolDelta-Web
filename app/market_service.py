import os
import json
from flask import current_app

class MarketService:
    def __init__(self):
        self._plugins = None
        self._packages = None
        self._id_map = None

    def get_market_dir(self):
        return current_app.config["PLUGIN_MARKET_DIR"]

    def scan(self):
        mdir = self.get_market_dir()
        self._plugins = []
        self._packages = []
        self._id_map = {}
        if not os.path.isdir(mdir):
            os.makedirs(mdir, exist_ok=True)
            return
        for d in sorted(os.listdir(mdir)):
            full = os.path.join(mdir, d)
            if not os.path.isdir(full):
                continue
            datapath = os.path.join(full, "datas.json")
            if not os.path.isfile(datapath):
                continue
            with open(datapath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "plugin-ids" in data:
                self._packages.append({
                    "name": d,
                    "display_name": d.replace("[pkg]", ""),
                    "author": data.get("author", "?"),
                    "version": data.get("version", "0.0.0"),
                    "description": data.get("description", ""),
                    "plugin_ids": data.get("plugin-ids", []),
                    "is_package": True,
                })
            elif data.get("plugin-id") or data.get("plugin-type"):
                pid = data.get("plugin-id", d)
                has_readme = os.path.isfile(os.path.join(full, "readme.md")) or os.path.isfile(os.path.join(full, "readme.txt"))
                self._plugins.append({
                    "id": pid,
                    "name": d,
                    "author": data.get("author", "?"),
                    "version": data.get("version", "0.0.0"),
                    "description": data.get("description", ""),
                    "plugin_type": data.get("plugin-type", "classic"),
                    "pre_plugins": data.get("pre-plugins", {}),
                    "has_readme": has_readme,
                    "dir": full,
                })
                self._id_map[pid] = d

    def get_plugins(self, refresh=False):
        if refresh or self._plugins is None:
            self.scan()
        return self._plugins or []

    def get_packages(self, refresh=False):
        if refresh or self._packages is None:
            self.scan()
        return self._packages or []

    def get_plugin_data(self, plugin_id, refresh=False):
        plugins = self.get_plugins(refresh)
        for p in plugins:
            if p["id"] == plugin_id:
                return p
        return None

    def search(self, keyword, by="name"):
        plugins = self.get_plugins()
        kw = keyword.lower()
        if by == "name":
            return [p for p in plugins if kw in p["name"].lower() or kw in p["id"].lower()]
        elif by == "author":
            return [p for p in plugins if kw in p["author"].lower()]
        return plugins

market_service = MarketService()
