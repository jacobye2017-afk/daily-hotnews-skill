"""渲染最终的选题卡给用户 + 输出结构化 JSON（给 4090 用）。"""
import json
import os
from datetime import datetime


MOOD_EMOJI = {
    "energetic": "⚡",
    "serious": "📰",
    "funny": "😂",
    "mysterious": "🕵️",
    "shocking": "💥",
}

DIRECTION_EMOJI = {
    "AI": "🤖",
    "美国": "🇺🇸",
    "世界": "🌍",
    "中国": "🇨🇳",
    "财经": "💰",
    "其他": "📌",
}


def rank_and_format(items: list, top_n: int = 10, direction: str = None) -> dict:
    """排序 + 取 Top N + 生成文字报告 + 结构化 JSON。

    返回:
        {
            "report": 字符串，适合飞书展示,
            "json_items": 列表，适合复制给 4090,
            "stats": 统计信息,
        }
    """
    # 只要已经打分的
    scored = [it for it in items if "scores" in it]

    # 按方向过滤
    if direction and direction != "all":
        scored = [it for it in scored if it.get("direction") == direction]

    # 按总分排序
    scored.sort(key=lambda x: -x["scores"]["total"])
    top = scored[:top_n]

    # 生成结构化 JSON（给 4090 用）
    json_items = []
    for i, it in enumerate(top, 1):
        json_items.append({
            "rank": i,
            "title": it["title"],  # 原标题（可能英文，留作溯源）
            "title_cn": it.get("title_cn") or it["title"],  # 中文标题，缺省降级原标题
            "source": it["source"],
            "url": it.get("url", ""),
            "posted_at": datetime.fromtimestamp(it.get("posted_ts", 0)).isoformat() if it.get("posted_ts") else "",
            "hotness": it.get("hotness", 0),
            "scores": it["scores"],
            "angles": it.get("angles", []),
            "keywords": it.get("keywords", []),
            "suggested_duration_sec": it.get("suggested_duration_sec", 45),
            "mood": it.get("mood", "energetic"),
            "direction": it.get("direction", "其他"),
            "desc": (it.get("desc") or "")[:200],
        })

    # 生成人看的报告
    report_lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    direction_label = f" · {direction}" if direction and direction != "all" else ""
    report_lines.append(f"🎬 短视频选题 Top {len(top)} · {now}{direction_label}")
    report_lines.append(f"   已筛选 {len(scored)} 条 24h 内热点")
    report_lines.append("")

    for item in json_items:
        rank = item["rank"]
        mood_e = MOOD_EMOJI.get(item["mood"], "⚡")
        dir_e = DIRECTION_EMOJI.get(item["direction"], "📌")
        s = item["scores"]

        display_title = item.get("title_cn") or item["title"]
        report_lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report_lines.append(f"【#{rank}】{dir_e} {display_title}")
        report_lines.append(f"     {mood_e} {item['direction']} | {item['source']} | 热度 {item['hotness']}")
        report_lines.append(f"     📊 打分: 话题{s['topicality']}/视觉{s['visual_impact']}/病毒{s['viral_potential']} = {s['total']}/30")
        if item["angles"]:
            report_lines.append(f"     🎯 角度建议:")
            for j, ang in enumerate(item["angles"], 1):
                report_lines.append(f"         {j}. {ang}")
        if item["keywords"]:
            report_lines.append(f"     🏷  {' '.join(item['keywords'])}")
        report_lines.append(f"     ⏱  建议 {item['suggested_duration_sec']}s  |  🔗 {item['url']}")
        report_lines.append("")

    # 尾部：统计 + JSON 位置提示
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report_lines.append(f"💾 结构化 JSON 已生成，可复制给 4090 的 AI 视频工作流")

    report = "\n".join(report_lines)

    # 方向分布
    from collections import Counter
    direction_counts = Counter(it["direction"] for it in top)

    return {
        "report": report,
        "json_items": json_items,
        "stats": {
            "total_scored": len(scored),
            "top_n": len(top),
            "directions": dict(direction_counts),
        },
    }


def save_json(json_items: list, output_dir: str = None) -> str:
    """把选题 JSON 存一份留档。"""
    if output_dir is None:
        output_dir = os.path.expanduser("~/.openclaw/workspace-scout/output")
    os.makedirs(output_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"topics_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(json_items, f, ensure_ascii=False, indent=2)
    return path


if __name__ == "__main__":
    # 测试
    fake = [{
        "title": "OpenAI 发布 GPT-5",
        "source": "HackerNews",
        "url": "https://...",
        "posted_ts": 1700000000,
        "hotness": 1500,
        "direction": "AI",
        "desc": "",
        "scores": {"topicality": 10, "visual_impact": 8, "viral_potential": 10, "total": 28},
        "angles": ["实测 GPT-5", "对比 GPT-4", "打工人的饭碗"],
        "keywords": ["#GPT5", "#OpenAI"],
        "suggested_duration_sec": 45,
        "mood": "energetic",
    }]
    out = rank_and_format(fake, top_n=5)
    print(out["report"])
