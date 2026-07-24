"""
ToolDelta-Web 规范自检脚本
- 默认 10 轮（可通过环境变量 ROUNDS 覆盖）
- 每轮启动独立子进程运行 run_full_test.py，确保状态隔离
- 汇总结果并写入 selfcheck_summary.txt
"""
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

ROUNDS = int(os.environ.get("ROUNDS", "10"))
if ROUNDS < 1:
    ROUNDS = 10

PASS_LINE_RE = re.compile(r"测试结果:\s*(\d+)\s*通过\s*/\s*(\d+)\s*失败")


def run_round(round_no):
    """运行一轮完整测试，返回 (passed, failed, total, elapsed_seconds, raw_output)。"""
    print(f"\n{'=' * 60}")
    print(f"  自检第 {round_no}/{ROUNDS} 轮")
    print(f"{'=' * 60}")
    env = os.environ.copy()
    # 每轮使用独立临时目录，避免跨轮状态污染
    env["TOOLDELTA_DIR"] = f"/tmp/td_selfcheck_r{round_no}/ToolDelta"
    t0 = time.time()
    proc = subprocess.Popen(
        [sys.executable, "-u", "run_full_test.py"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    output, _ = proc.communicate(timeout=180)
    elapsed = time.time() - t0
    passed = failed = total = 0
    for line in output.splitlines():
        m = PASS_LINE_RE.search(line)
        if m:
            passed = int(m.group(1))
            failed = int(m.group(2))
            total = passed + failed
            break
    success = proc.returncode == 0 and failed == 0
    print(f"  第 {round_no} 轮: {passed}通过 / {failed}失败 / {total}总计  ({elapsed:.1f}s)")
    if not success:
        # 失败时打印最后若干行便于定位
        tail = "\n".join(output.splitlines()[-30:])
        print(tail)
    return passed, failed, total, elapsed, output


def main():
    rounds = []
    overall_passed = 0
    overall_failed = 0
    total = 0

    for i in range(1, ROUNDS + 1):
        passed, failed, total, elapsed, output = run_round(i)
        rounds.append((i, passed, failed, total, elapsed, output))
        overall_passed += passed
        overall_failed += failed

    summary_lines = [
        "=" * 60,
        "  ToolDelta-Web 自检报告（%d 轮）" % ROUNDS,
        "=" * 60,
        "",
        "  总断言次数: %d（%d 轮 × 每轮 %d 项）" % (overall_passed + overall_failed, ROUNDS, total),
        "  总通过: %d  |  总失败: %d" % (overall_passed, overall_failed),
        "",
        "  各轮详情:",
    ]
    for i, passed, failed, total, elapsed, _ in rounds:
        marker = "✓" if failed == 0 else "✗"
        summary_lines.append(
            "    第 %2d轮: %d通过 / %d失败  %s  %.1fs  [PASS行=%d]" % (
                i, passed, failed, marker, elapsed, passed
            )
        )
    summary_lines.append("")
    if overall_failed == 0:
        summary_lines.append("  ★★★ %d 轮全部通过（%d 次断言 0 失败），所有功能稳定可靠 ★★★" % (ROUNDS, overall_passed + overall_failed))
    else:
        summary_lines.append("  ✗✗✗ 存在失败项：%d 次断言未通过 ✗✗✗" % overall_failed)
    summary_lines.append("")

    summary_text = "\n".join(summary_lines)
    print("\n" + summary_text)

    with open(os.path.join(ROOT, "selfcheck_summary.txt"), "w", encoding="utf-8") as f:
        f.write(summary_text)

    sys.exit(0 if overall_failed == 0 else 1)


if __name__ == "__main__":
    main()
