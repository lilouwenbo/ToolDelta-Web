import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_or_create_secret_key():
    """加载或生成持久化 SECRET_KEY（instance/secret_key），避免会话被伪造（P1-2）。"""
    key_file = os.path.join(BASE_DIR, "instance", "secret_key")
    try:
        if os.path.isfile(key_file):
            with open(key_file, "r", encoding="utf-8") as f:
                k = f.read().strip()
                if k:
                    return k
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        k = secrets.token_hex(32)
        with open(key_file, "w", encoding="utf-8") as f:
            f.write(k)
        os.chmod(key_file, 0o600)  # 仅本用户可读写
        return k
    except Exception:
        # 极端场景（如只读文件系统）退化为内存随机值，绝不阻塞启动
        return secrets.token_hex(32)


def _env_bool(name, default=False):
    return os.environ.get(name, "true" if default else "false").lower() in ("1", "true", "yes", "on")


class Config:
    # SECRET_KEY 安全加固（P1-2）：
    # 1) 优先读环境变量 SECRET_KEY（生产必须显式设置）；
    # 2) 否则读 instance/secret_key（首次运行自动生成并持久化），保证重启后密钥稳定；
    # 3) 都不存在则回退内存随机值（仅本进程有效，重启即失效）。
    SECRET_KEY = os.environ.get("SECRET_KEY") or _load_or_create_secret_key()

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

    # 插件市场预设源（列表，供前端下拉选择）
    MARKET_SOURCES = [
        {"name": "官方源", "url": "https://pm.tooldelta.top"},
        {"name": "镜像源 1", "url": "https://github.yuansi.xyz/https://raw.githubusercontent.com/ToolDelta-Basic/PluginMarket/main"},
        {"name": "镜像源 2", "url": "https://github.tooldelta.top/https://raw.githubusercontent.com/ToolDelta-Basic/PluginMarket/main"},
        {"name": "镜像源 3", "url": "https://github.ghfast.top/https://raw.githubusercontent.com/ToolDelta-Basic/PluginMarket/main"},
    ]

    TOOLDELTA_CLASSIC_PLUGIN_PATH = os.path.join(TOOLDELTA_DIR, "插件文件", "ToolDelta类式插件")
    TOOLDELTA_PLUGIN_CFG_DIR = os.path.join(TOOLDELTA_DIR, "插件配置文件")
    TOOLDELTA_PLUGIN_DATA_DIR = os.path.join(TOOLDELTA_DIR, "插件数据文件")

    # Web 面板自身数据目录（收藏等用户数据），独立于 ToolDelta 安装目录
    WEB_DATA_DIR = os.path.join(BASE_DIR, "data")
