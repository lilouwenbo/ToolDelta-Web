import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _env_bool(name, default=False):
    return os.environ.get(name, "true" if default else "false").lower() in ("1", "true", "yes", "on")


class Config:
    # 安全相关保持原样（不在此处做安全加固，仅保证可用）
    SECRET_KEY = os.environ.get("SECRET_KEY", "tooldelta-web-secret-key")

    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    # 统一 DEBUG：默认关闭，可通过环境变量开启；避免与 run.py 的 debug 参数相互矛盾
    DEBUG = _env_bool("DEBUG", False)

    # ToolDelta 主目录：优先使用环境变量 TOOLDELTA_DIR，
    # 未设置时回退到项目目录下的 ToolDelta 子目录（跨平台可用）。
    # 注意：Linux 环境下请通过环境变量 TOOLDELTA_DIR 指向真实的 ToolDelta 安装目录。
    TOOLDELTA_DIR = os.environ.get("TOOLDELTA_DIR") or os.path.join(BASE_DIR, "ToolDelta")
    TOOLDELTA_MAIN = os.path.join(TOOLDELTA_DIR, "main.py")

    # 出厂主程序包（重置功能使用）：放在 web 项目次级目录，
    # 避免把主程序直接解压到 web 根目录造成文件混合。
    TOOLDELTA_SOURCE_ZIP = os.path.join(BASE_DIR, "tooldelta_source", "ToolDelta-main.zip")

    PLUGIN_MARKET_DIR = os.path.join(BASE_DIR, "plugin_market")
    BACKUP_DIR = os.path.join(BASE_DIR, "backups")
    BRIDGE_PLUGIN_DIR = os.path.join(BASE_DIR, "bridge_plugin")

    TOOLDELTA_CLASSIC_PLUGIN_PATH = os.path.join(TOOLDELTA_DIR, "插件文件", "ToolDelta类式插件")
    TOOLDELTA_PLUGIN_CFG_DIR = os.path.join(TOOLDELTA_DIR, "插件配置文件")
    TOOLDELTA_PLUGIN_DATA_DIR = os.path.join(TOOLDELTA_DIR, "插件数据文件")
