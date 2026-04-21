"""中文全网热榜聚合 - 使用 orz.ai/api/v1/dailynews 作为后端

orz.ai 支持的平台：
baidu, shaoshupai, weibo, zhihu, 36kr, 52pojie, bilibili, douban,
hupu, tieba, juejin, douyin, v2ex, jinritoutiao, tenxunwang,
stackoverflow, github, hackernews, sina_finance, eastmoney, xueqiu, cls
"""
import requests
import time

BASE_URL = "https://orz.ai/api/v1/dailynews/"

# 按方向分类的平台
# direction 字段：AI / 美国 / 世界 / 中国 / 其他
PLATFORMS = [
    # AI / 科技（优先）
    ("hackernews", "HackerNews",  "AI"),
    ("github",     "GitHub Trending", "AI"),
    ("36kr",       "36氪",        "AI"),
    ("juejin",     "掘金",        "AI"),

    # 中国综合热点
    ("weibo",      "微博热搜",    "中国"),
    ("zhihu",      "知乎热榜",    "中国"),
    ("baidu",      "百度热搜",    "中国"),
    ("jinritoutiao", "今日头条",  "中国"),
    ("douyin",     "抖音热点",    "中国"),
    ("bilibili",   "B站热门",     "中国"),

    # 财经（看全球经济动向）
    ("sina_finance", "新浪财经",  "世界"),
    ("xueqiu",     "雪球热股",    "世界"),
]


def fetch_platform(platform_id: str, timeout: int = 10) -> list:
    """抓取单个平台的热榜。"""
    url = f"{BASE_URL}?platform={platform_id}"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  ⚠️ {platform_id} 抓取失败: {e}")
        return []

    items = data.get("data", [])
    if not isinstance(items, list):
        return []

    now_ts = int(time.time())
    results = []
    for item in items[:30]:
        title = (item.get("title") or "").strip()
        if not title:
            continue

        # 热度 - orz.ai 给的 hot 字段经常是空，用 index 反推
        hot_raw = item.get("hot") or item.get("score") or ""
        hotness = _parse_hotness(hot_raw)
        if hotness == 0:
            # 用 rank 反推热度（排第 1 → 100，第 30 → 1）
            index = item.get("index") or item.get("rank") or len(results) + 1
            hotness = max(1, 100 - int(index) * 3)

        results.append({
            "title": title,
            "url": item.get("url") or item.get("link") or "",
            "hotness": hotness,
            "posted_ts": now_ts,  # 这个 API 不给时间戳，默认当前
            "desc": item.get("desc") or item.get("description") or "",
        })
    return results


def _parse_hotness(hot) -> int:
    """把 '127万' / '1.2w' / 数字字符串解析成整数。"""
    if isinstance(hot, (int, float)):
        return int(hot)
    if not hot:
        return 0
    s = str(hot).strip().replace(",", "").replace(" ", "")
    try:
        if s.endswith("万") or s.endswith("w") or s.endswith("W"):
            num = float(s[:-1])
            return int(num * 10000)
        if s.endswith("亿"):
            num = float(s[:-1])
            return int(num * 100000000)
        if s.endswith("k") or s.endswith("K"):
            num = float(s[:-1])
            return int(num * 1000)
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def fetch_all(platforms=None, max_per_platform=15) -> list:
    """聚合所有平台。"""
    if platforms is None:
        platforms = PLATFORMS

    all_items = []
    for pid, pname, direction in platforms:
        items = fetch_platform(pid)
        items = items[:max_per_platform]
        for it in items:
            it["source"] = pname
            it["source_id"] = pid
            it["direction"] = direction
        all_items.extend(items)
        print(f"  ✅ {pname}: {len(items)} 条")

    return all_items


if __name__ == "__main__":
    items = fetch_all()
    print(f"\n总共抓到 {len(items)} 条")
    if items:
        print(f"\n样例:")
        for it in items[:5]:
            print(f"  [{it['source']}] {it['title']} (hot={it['hotness']})")
