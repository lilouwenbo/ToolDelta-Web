"""状态仪表盘聚合数据服务（类单例 + init_app，风格B：无后台线程，纯聚合只读）。

职责：
- 聚合系统资源（CPU/内存/磁盘）、ToolDelta 运行状态、看门狗开关、连接数、插件数。
- 所有指标均用 try/except 包裹，异常时回退为 0 / None，绝不让 get_dashboard() 抛异常。
- 复用既有服务（tooldelta_manager / plugin_service / connection_service / watchdog_service），
  这些都是独立模块，不会与本项目产生循环 import。

get_dashboard() 既可被 /api/dashboard 路由调用，也可被测试直接调用（此时 app 可能为 None，
会用 os.getcwd() 作为磁盘采样基准目录）。
"""
import os
import time
import shutil

from app.tooldelta_manager import tooldelta_manager
from app.plugin_service import plugin_service
from app.connection_service import list_connections
from app.watchdog_service import watchdog_service
from app.log_service import log_service


class DashboardService:
    def __init__(self):
        self.version = "1.0"
        self.app = None

    # ─── 初始化 ───────────────────────────────────────────────

    def init_app(self, app):
        """保存应用快照（基准目录 / 版本），并兜底注册仪表盘蓝图（幂等）。"""
        self.app = app
        # 快照版本号（风格B：纯只读聚合，不依赖后台线程）
        self.version = "1.0"

        try:
            log_service.info("状态仪表盘服务已初始化", "DASHBOARD")
        except Exception:
            pass

        # 兼容：若主应用未注册本蓝图，则在此兜底注册（幂等，避免重复注册）
        try:
            from app.routes.dashboard import bp as dashboard_bp
            if "dashboard" not in getattr(app, "blueprints", {}):
                app.register_blueprint(dashboard_bp)
        except Exception:
            pass

    # ─── CPU 近似采样（/proc/stat 两次采样） ──────────────────

    @staticmethod
    def _sample_cpu() -> float:
        """读 /proc/stat 首行，隔 0.1s 再读，按 (1 - delta_idle/total) 计算使用率。

        非 Linux 或读不到时返回 0.0。
        """
        try:
            if not os.path.isfile("/proc/stat"):
                return 0.0

            def _read():
                with open("/proc/stat", "r") as f:
                    line = f.readline()
                parts = [int(x) for x in line.split()[1:]]
                idle = parts[3]
                total = sum(parts)
                return idle, total

            idle1, total1 = _read()
            time.sleep(0.1)
            idle2, total2 = _read()

            total_delta = total2 - total1
            if total_delta <= 0:
                return 0.0
            idle_delta = idle2 - idle1
            cpu = (1.0 - idle_delta / total_delta) * 100.0
            return round(max(0.0, min(100.0, cpu)), 1)
        except Exception:
            return 0.0

    # ─── 内存（/proc/meminfo） ───────────────────────────────

    @staticmethod
    def _mem_info():
        """返回 (mem_percent, mem_used_mb, mem_total_mb)。取不到给 (0.0, 0, 0)。"""
        try:
            if not os.path.isfile("/proc/meminfo"):
                return 0.0, 0, 0
            info = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    kv = line.split(":")
                    if len(kv) != 2:
                        continue
                    key = kv[0].strip()
                    try:
                        val = int(kv[1].strip().split()[0])
                    except (ValueError, IndexError):
                        continue
                    info[key] = val
            total = info.get("MemTotal", 0)
            if total <= 0:
                return 0.0, 0, 0
            available = info.get("MemAvailable")
            if available is None:
                # 旧内核无 MemAvailable，用 MemFree + Buffers + Cached 近似
                available = (
                    info.get("MemFree", 0)
                    + info.get("Buffers", 0)
                    + info.get("Cached", 0)
                )
            used = total - available
            percent = used / total * 100.0
            return round(percent, 1), int(used / 1024), int(total / 1024)
        except Exception:
            return 0.0, 0, 0

    # ─── 磁盘（shutil.disk_usage） ───────────────────────────

    @staticmethod
    def _disk_info(base_dir: str):
        """返回 (disk_percent, disk_free_gb)。取不到给 (0.0, 0.0)。"""
        try:
            usage = shutil.disk_usage(base_dir)
            percent = usage.used / usage.total * 100.0
            free_gb = usage.free / (1024 ** 3)
            return round(percent, 1), round(free_gb, 2)
        except Exception:
            return 0.0, 0.0

    def _base_dir(self) -> str:
        try:
            if self.app is not None:
                return os.path.dirname(self.app.root_path)
        except Exception:
            pass
        return os.getcwd()

    # ─── 聚合入口 ─────────────────────────────────────────────

    def get_dashboard(self) -> dict:
        """聚合所有仪表盘指标；任何子项异常都回退为 0 / None / 空，绝不抛异常。"""
        # 系统资源
        try:
            cpu_percent = self._sample_cpu()
        except Exception:
            cpu_percent = 0.0

        try:
            mem_percent, mem_used_mb, mem_total_mb = self._mem_info()
        except Exception:
            mem_percent, mem_used_mb, mem_total_mb = 0.0, 0, 0

        try:
            disk_percent, disk_free_gb = self._disk_info(self._base_dir())
        except Exception:
            disk_percent, disk_free_gb = 0.0, 0.0

        # ToolDelta 运行状态（直接复用既有接口）
        try:
            tooldelta_status = tooldelta_manager.get_status() or {}
        except Exception:
            tooldelta_status = {}

        # 看门狗开关
        try:
            watchdog_enabled = bool(watchdog_service.get_config().get("enabled", False))
        except Exception:
            watchdog_enabled = False

        # 连接数
        try:
            connections = list_connections()
            connections_count = len(connections) if connections is not None else 0
        except Exception:
            connections_count = 0

        # 插件数
        try:
            plugins = plugin_service.list_plugins()
            plugins_count = len(plugins) if plugins else 0
        except Exception:
            plugins_count = 0

        return {
            "system": {
                "cpu_percent": cpu_percent,
                "mem_percent": mem_percent,
                "mem_used_mb": mem_used_mb,
                "mem_total_mb": mem_total_mb,
                "disk_percent": disk_percent,
                "disk_free_gb": disk_free_gb,
            },
            "tooldelta": tooldelta_status,
            "panel": {
                "version": self.version,
                "watchdog_enabled": watchdog_enabled,
                "connections_count": connections_count,
                "plugins_count": plugins_count,
            },
        }


# 类单例
dashboard_service = DashboardService()
