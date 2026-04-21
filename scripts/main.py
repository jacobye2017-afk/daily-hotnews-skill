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


def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else ""
    print(f"📝 收到指令: {msg!r}")
    print()

    direction = detect_direction(msg)
    top_n = detect_top_n(msg)
    print(f"🧭 方向: {direction}  |  📊 Top: {top_n}")
    print()

    # 1. 抓取
    print("=" * 50)
    print("📡 STEP 1: 抓取全网热点")
    print("=" * 50)
    items = aggregator.fetch_all()
    if not items:
        print("❌ 没抓到任何数据")
        return 1

    # 2. AI 打分
    print()
    print("=" * 50)
    print("🤖 STEP 2: MiniMax 打分")
    print("=" * 50)
    scored = scorer.score_all(items, max_items=60)

    # 3. 排序 + 格式化
    print()
    print("=" * 50)
    print("🎬 STEP 3: 生成选题报告")
    print("=" * 50)
    out = formatter.rank_and_format(scored, top_n=top_n, direction=direction)

    # 存 JSON 留档
    try:
        json_path = formatter.save_json(out["json_items"])
        print(f"💾 JSON 已存档: {json_path}")
    except Exception as e:
        print(f"⚠️ 存 JSON 失败: {e}")

    print()
    print(out["report"])

    # 最后再打印 JSON（方便手动 copy 给 4090）
    print()
    print("=" * 50)
    print("📋 STRUCTURED JSON (copy to 4090)")
    print("=" * 50)
    import json
    print(json.dumps(out["json_items"], ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
