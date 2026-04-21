"""Scout 主入口: 接用户消息 → 路由到抓取+打分+格式化。"""
import sys
import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import aggregator
import scorer
import formatter


def detect_direction(msg: str) -> str:
    """从用户消息里识别方向偏好。"""
    m = (msg or "").lower()
    if any(k in msg for k in ["ai", "AI", "人工智能", "科技"]):
        return "AI"
    if any(k in msg for k in ["美国", "US", "us news", "美国新闻", "美国本土"]):
        return "美国"
    if any(k in msg for k in ["世界", "world", "国际", "国外"]):
        return "世界"
    if any(k in msg for k in ["中国", "国内", "中文"]):
        return "中国"
    return "all"


def detect_top_n(msg: str) -> int:
    """从用户消息里识别 top N。默认 10。"""
    m = re.search(r"top\s*(\d+)|前\s*(\d+)|(\d+)\s*条", msg or "", re.I)
    if m:
        n = next((int(x) for x in m.groups() if x), 10)
        return min(max(n, 3), 30)
    return 10


def log(msg: str):
    """进度只写 stderr，不污染 stdout（stdout 会回传给 agent LLM）。"""
    print(msg, file=sys.stderr, flush=True)


def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else ""
    direction = detect_direction(msg)
    top_n = detect_top_n(msg)
    log(f"📝 {msg!r} | 🧭 {direction} | 📊 Top {top_n}")

    log("📡 抓取全网热点…")
    items = aggregator.fetch_all()
    if not items:
        print("❌ 没抓到任何数据")
        return 1

    log("🤖 MiniMax 打分…")
    scored = scorer.score_all(items, max_items=60)

    log("🎬 生成选题报告…")
    out = formatter.rank_and_format(scored, top_n=top_n, direction=direction)

    try:
        json_path = formatter.save_json(out["json_items"])
        log(f"💾 JSON 存档: {json_path}")
    except Exception as e:
        log(f"⚠️ 存 JSON 失败: {e}")

    # stdout 只输出最终报告（回传给 agent / 用户）
    print(out["report"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
