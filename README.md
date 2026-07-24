# ToolDelta-Web

ToolDelta 的 Web 管理面板。提供可视化的控制台、插件管理、备份与恢复、重置出厂等功能，让你在浏览器里轻松管理 ToolDelta 主程序。

## 功能特性

- **控制台**：实时启动 / 停止 / 重启 ToolDelta 主程序，交互式命令输入与彩色输出
- **插件管理**：插件市场浏览、安装 / 启用 / 停用、预设插件一键安装
- **备份与恢复**：一键备份用户插件与配置，支持恢复失败自动回滚
- **重置出厂**：删除原主程序与用户数据并解压出厂包，完整复位到初始状态
- **用户与权限**：管理员 / 普通用户角色，登录鉴权
- **其他**：系统信息、日志查看、壁纸设置等

## 目录结构

```
ToolDelta-Web/
├── app/                      # Flask 应用
│   ├── routes/               # 路由层（api.py / auth.py / files.py）
│   ├── templates/            # 前端页面模板
│   ├── static/               # 静态资源（含本地化的 socket.io）
│   ├── *_service.py          # 业务服务（备份 / 插件 / 日志 / 壁纸等）
│   ├── tooldelta_manager.py  # ToolDelta 主程序进程管理
│   └── socket_events.py      # WebSocket 事件
├── tooldelta_source/         # 出厂主程序包 ToolDelta-main.zip（重置功能使用）
├── config.py                 # 配置（TOOLDELTA_DIR / TOOLDELTA_SOURCE_ZIP 等）
├── run.py                    # 启动入口
├── requirements.txt          # Web 面板依赖（联网安装用）
├── wheels/                   # 随附离线依赖包（无需联网，初始化优先使用）
├── LICENSE                   # MIT 许可证
└── README.md
```

## 环境要求

- Python 3.8+
- pip

## 安装依赖

面板在**首次初始化**时会弹出安装向导，让你选择依赖安装方式（也可在命令行手动安装）：

- **本地安装（离线，推荐用于共享服务器 / 无外网环境）**：使用随项目 `wheels/` 目录随附的
  离线依赖包（含 grpcio / numpy / protobuf 等），**无需联网**，可避免共享服务器因请求限流
  导致安装失败。

  > ⚠️ 离线包为发布时打包的固定版本，**可能版本较旧**，并非各依赖的最新版。

- **网络安装（在线，获取最新版本）**：从 PyPI / 国内镜像源联网下载并安装最新版本，需要联网。

命令行手动安装：

- 本地离线安装：

  ```bash
  pip install --no-index --find-links ./wheels -r ./wheels/requirements.txt
  ```

- 联网安装（最新版）：

  ```bash
  pip install -r requirements.txt
  ```

> 若启动时检测到依赖缺失，面板会自动从 `wheels/` 离线安装兜底；仅当离线包不适配当前
> 平台 / Python 版本时，才提示改用网络安装。

## 配置

配置位于 `config.py`，可用环境变量覆盖：

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `TOOLDELTA_DIR` | ToolDelta 主程序运行目录（放在 web 项目次级目录，避免主程序与 web 根目录混在一起） | 项目下 `ToolDelta/` |
| `TOOLDELTA_SOURCE_ZIP` | 出厂主程序包路径（重置功能使用） | `tooldelta_source/ToolDelta-main.zip` |
| `HOST` / `PORT` | 监听地址与端口 | `0.0.0.0` / `5000` |
| `DEBUG` | 调试模式 | 关闭 |

> 首次使用请通过 `/setup` 页面初始化管理员账号。

## 运行

```bash
python run.py
```

启动后访问 `http://<HOST>:<PORT>`。

## 重置出厂

面板中的「重置」操作会：

1. 清空 `TOOLDELTA_DIR` 内的全部内容（主程序与用户插件 / 配置 / 数据一并删除）；
2. 解压 `ToolDelta-main.zip` 恢复出厂主程序。

出厂包顶层目录（如 `ToolDelta-main/`）会在解压时自动剥离，确保 `main.py` 正确落在 `TOOLDELTA_DIR` 下，而不会出现 `TOOLDELTA_DIR/ToolDelta-main/main.py` 的嵌套。

## 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。
