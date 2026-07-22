# -*- coding: utf-8 -*-
"""ToolDelta-Web 规范自检入口（默认 10 轮）。

每轮：独立子进程 + 全新隔离环境运行 run_full_test.py（约 90 项断言），
循环 ROUND_COUNT 次后输出汇总并写入 selfcheck_summary.txt。

用法:
    python3 selfcheck.py            # 默认 10 轮
    ROUNDS=10 python3 selfcheck.py  # 显式指定轮数
"""
import subprocess, sys, re, time, os

TEST_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_full_test.py")
SUMMARY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "selfcheck_summary.txt")
ROUND_COUNT = int(os.environ.get("ROUNDS", "10"))

all_rounds = []
for i in range(1, ROUND_COUNT + 1):
    print(f"\n{'='*60}")
    print(f"  >>> 第 {i}/{ROUND_COUNT} 轮全量功能测试（独立进程 + 全新隔离环境）")
    print(f"{'='*60}\n")

    start = time.time()
    proc = subprocess.run(
        [sys.executable, TEST_SCRIPT],
        capture_output=True, text=True, timeout=300
    )
    elapsed = time.time() - start

    output = proc.stdout
    match = re.search(r"测试结果:\s*(\d+)\s*通过\s*/\s*(\d+)\s*失败\s*\(\s*共\s*(\d+)\)", output)
    if match:
        passed, failed, total = int(match.group(1)), int(match.group(2)), int(match.group(3))
    else:
        passed, failed, total = -1, -1, -1

    fail_items = [ln.strip() for ln in output.split("\n") if "[FAIL]" in ln]
    pass_count = sum(1 for ln in output.split("\n") if "[PASS]" in ln)

    all_rounds.append({
        "round": i, "passed": passed, "failed": failed, "total": total,
        "pass_lines": pass_count, "elapsed": elapsed,
        "fail_items": fail_items, "success": failed == 0
    })

    status = "✓ 全过" if failed == 0 else f"✗ {failed} 项失败"
    print(f"  本轮结果: {passed} 通过 / {failed} 失败 (共 {total})  [PASS行数={pass_count}]  | {status} | 耗时 {elapsed:.1f}s")
    if fail_items:
        print("  失败项:")
        for item in fail_items:
            print(f"    {item}")

# ========== 汇总 ==========
lines = []
lines.append(f"{'='*60}")
lines.append(f"  ToolDelta-Web 自检报告（{ROUND_COUNT} 轮）")
lines.append(f"{'='*60}")

all_pass = all(r["success"] for r in all_rounds)
total_passed = sum(r["passed"] for r in all_rounds if r["passed"] >= 0)
total_failed = sum(r["failed"] for r in all_rounds if r["failed"] >= 0)
total_assertions = total_passed + total_failed

lines.append(f"\n  总断言次数: {total_assertions}（{ROUND_COUNT} 轮 × 每轮 ~90 项）")
lines.append(f"  总通过: {total_passed}  |  总失败: {total_failed}")
lines.append(f"\n  各轮详情:")
for r in all_rounds:
    mark = "✓" if r["success"] else "✗"
    lines.append(f"    第{r['round']:2d}轮: {r['passed']}通过 / {r['failed']}失败  {mark}  {r['elapsed']:.1f}s  [PASS行={r['pass_lines']}]")

if all_pass:
    lines.append(f"\n  ★★★ {ROUND_COUNT} 轮全部通过（{total_assertions} 次断言 0 失败），所有功能稳定可靠 ★★★")
else:
    lines.append(f"\n  ✗ 存在失败轮次，需排查")
    for r in all_rounds:
        if not r["success"]:
            lines.append(f"    第{r['round']}轮失败项:")
            for item in r["fail_items"]:
                lines.append(f"      {item}")

report = "\n".join(lines)
print(report)

with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
    f.write(report + "\n")

sys.exit(0 if all_pass else 1)
