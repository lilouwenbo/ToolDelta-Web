# ToolDelta-Web 主程序集成分析与优化报告

> 生成时间：2026-07-23
> 范围：只读分析主程序（ToolDelta 1.3.5），评估与 Web 项目（ToolDelta-Web）集成相关的
> **持续优化 / 升级 / 修复 bug** 点。主程序代码保持只读，所有改动在 Web 侧完成。

---

## 一、本次已修复的高价值 Bug（头条）

### 1.1 Web 控制台彩色丢失的真正根因：rich 真彩 `38;2` 未被识别

**现象**：用户反馈"终端还是无法显示彩色字体"。

**链路复盘**（主程序只读结论）：
- 主程序 `print()` 走 `logging → rich`（`tooldelta/utils/fmts/logger.py` 的
  `CustomPrefixRichHandler`，经 `color_to_rich` 把 `§c` 等转成 `[#FF5555]` 这样的 hex 颜色）。
- rich 在**支持真彩的终端**（现代终端 / CI 普遍设置 `COLORTERM=truecolor`）下，
  渲染为**真彩 ANSI `38;2;r;g;b`**，而不是 16 色码。
- Web 侧 `ansi_to_html` 的 `_ANSI_COLORS` 只含 16 色（`0;31`/`1;31` …），
  `38;2;...` 真彩序列**完全丢色** → 彩色变纯文本。

**实测对照**：
| 环境 | rich 输出 | 旧逻辑结果 |
|---|---|---|
| 无 `COLORTERM` | 16 色 `91`/`32` | 有颜色（旧逻辑勉强匹配） |
| `COLORTERM=truecolor` | 真彩 `38;2;r;g;b` | **丢色（纯文本）** ← 用户真实环境 |
| `TERM=xterm-256color` | 256 色 `38;5;n` | 丢色 |

**上次"彩色修复"的盲区**：只修了少数 16 色路径，真彩主路径仍失效——这就是"还是不显示彩色"的原因。

**修复**（`app/tooldelta_manager.py` 的 `ansi_to_html` 重写）：
- 完整解析 SGR：`38;2;r;g;b`（真彩）、`38;5;n`（256 色）、背景 `48;2/48;5`、
  下划线(`4`)/斜体(`3`)/删除线(`9`)/粗体(`1`)。
- 新增 `_xterm256_to_hex()` 处理 256 色板；`_BASE16` 映射 16 色。
- 移除旧代码脆弱的 `<span>` 拼接 hack（`reset` 标志 + `html.replace("<span>","",1)` 误删风险），
  改为"样式状态机"逐段包裹。
- 先剥离 OSC / 字符集 / 非颜色 CSI 序列，避免裸控制字符残留成乱码。

**验证**：独立切片测试覆盖真彩红/绿、256 色、16 色、粗体、下划线(`§u`)、斜体(`§o`)、
删除线(`§S`)、背景色、裸 `§a`、混合真彩行——全部正确上色，无 `§` 残留；
真实 rich 真彩输出正确转 `<span style="color:#ff5555;">`。

---

## 二、主程序 vs Web：其余可优化 / 升级 / 已知限制

| # | 类别 | 发现 | 影响 | 建议（是否本次处理） |
|---|---|---|---|---|
| 2.1 | 修复 | **真彩 `38;2` 丢色**（见上） | 彩色日志变纯文本 | 已修复 |
| 2.2 | 已知限制 | **Windows 下无 pty**：Windows 回退 PIPE，rich 失去 TTY 判定，可能降级/丢失部分颜色 | Windows 用户彩色不全 | 设计限制，未来评估 `pywinpty` 或强制 `COLORTERM=truecolor` |
| 2.3 | 已知限制 | **主程序交互式 `input()` 提示在 Web 下阻塞**：config_loader / plugin_market / auths 等处 `input()` 在 Web 环境会卡住 | 部分运维操作在 Web 不可用 | 主程序约束，Web 侧只能避开触发，非本次可修 |
| 2.4 | 升级 | **前端未展示版本号**：ToolDelta 主程序版本（1.3.5）与 Web 版本均未在界面呈现 | 用户难判断版本 | 可选增强：设置页增加版本/构建哈希展示 |
| 2.5 | 升级 | **构建/发布无归档**：此前手工 `zip` 覆盖旧包，无法回溯 | 出问题无法回滚 | 已新增 `build.py` 每次构建自动归档 |
| 2.6 | 升级 | **自检无规范入口/轮数不固定**：此前有 10 轮与 20 轮两套脚本 | 质量门禁不统一 | 已确立 `selfcheck.py` 固定 10 轮 |
| 2.7 | 升级 | **缺少 CI**：打包/自检未接入自动化 | 每次靠手工跑 | 可选增强：GitHub Actions 跑 `selfcheck.py` + `build.py` |
| 2.8 | 确认(非 bug) | `-l 1` 启动参数合法：`launch_args["l"]=="1"` → `start_tool_delta()` 非交互启动 | — | 确认无误 |
| 2.9 | 确认(链路成立) | 命令链路：Web `send_command` 写 stdin → 主程序 `command_readline_proc` 线程 `input()` 逐行读 | 控制台命令可下发 | 链路成立 |

---

## 三、构建存档机制（build.py + archives/）

**目标**：每次构建发布都保留一份归档副本（带版本/时间戳/短哈希），不覆盖。

**行为**：
1. 打包当前项目为发布 zip（排除 `.git` / `__pycache__` / `backups` / `ToolDelta` /
   `plugin_market` / `instance` / `data` / `archives` / `*.log` / `*.db` / 旧的 `ToolDelta-Web.zip`）。
2. 存入 `archives/`，文件名形如 `ToolDelta-Web_1.0.0_20260722-225026_00ca1ea.zip`。
3. 同步更新根目录 `ToolDelta-Web.zip` 作为"最新交付物"。
4. 在 `archives/manifest.json` 追加记录（版本/时间/git短哈希/sha256/大小/文件数）。

**用法**：
```bash
python3 build.py                 # 读 VERSION 作为版本号
BUILD_VERSION=1.1.0 python3 build.py
SKIP_LATEST=1 python3 build.py  # 只归档，不覆盖最新交付物
```
> 注：`archives/` 与 `*.zip` 已在 `.gitignore` 中排除，构建产物不进 git。

---

## 四、规范自检入口（selfcheck.py，10 轮）

**目标**：将端到端自检固定为 **10 轮**（用户要求），作为唯一质量门禁。

**行为**：每轮启动独立子进程 + 全新隔离 `TOOLDELTA_DIR`，运行 `run_full_test.py`
（138 项断言，覆盖 P1/P2 模块：启动/停止/重启/日志/收藏/连接/看门狗/调度/仪表盘等），
循环 10 次后汇总并写 `selfcheck_summary.txt`。

**用法**：
```bash
python3 selfcheck.py            # 默认 10 轮
ROUNDS=10 python3 selfcheck.py  # 显式指定
```

**本次验证结果**：10 轮全部通过，**1380 次断言 0 失败**（每轮 138 通过 / 0 失败）。
控制台彩色改动经单轮 138 项回归与 10 轮自检确认无回归。

---

## 五、后续可选增强（未在本轮执行）
- 前端设置页展示 ToolDelta 版本 / Web 版本 / 构建哈希。
- Windows pty 真彩支持（`pywinpty` 或强制 `COLORTERM=truecolor`）。
- GitHub Actions：push 时自动 `selfcheck.py` + `build.py`。
