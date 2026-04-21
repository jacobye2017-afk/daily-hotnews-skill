"""Reddit hot posts - 美国新闻 / AI / 世界新闻。

使用 Reddit 的公开 JSON API（不需要 auth，有速率限制）:
https://www.reddit.com/r/{sub}/hot.json
"""
import requests
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh) Scout/1.0",
}

# 按方向分类的 subreddits
SUBREDDITS = [
    # AI / 科技
    ("artificial",    "r/artificial",    "AI"),
    ("LocalLLaMA",    "r/LocalLLaMA",    "AI"),
    ("OpenAI",        "r/OpenAI",        "AI"),
    ("singularity",   "r/singularity",   "AI"),
    ("MachineLearning", "r/MachineLearning", "AI"),
    ("technology",    "r/technology",    "AI"),

    # 美国本土（时事 + 政治）
    ("news",          "r/news",          "美国"),
    ("politics",      "r/politics",      "美国"),
    ("UpliftingNews", "r/UpliftingNews", "美国"),
    ("Economics",     "r/Economics",     "美国"),

    # 美股 / 财经
    ("stocks",        "r/stocks",        "财经"),
    ("wallstreetbets","r/wallstreetbets","财经"),
    ("investing",     "r/investing",     "财经"),
    ("StockMarket",   "r/StockMarket",   "财经"),

    # 世界时事
    ("worldnews",     "r/worldnews",     "世界"),
    ("geopolitics",   "r/geopolitics",   "世界"),
]


def fetch_subreddit(sub: str, limit: int = 15, timeout: int = 10) -> list:
    """抓一个 subreddit 的 hot posts。"""
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}&t=day"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  ⚠️ r/{sub} 抓取失败: {e}")
        return []

    now = int(time.time())
    cutoff_24h = now - 24 * 3600
    results = []

    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        title = (post.get("title") or "").strip()
        if not title:
            continue

        created = int(post.get("created_utc", now))
        if created < cutoff_24h:
            continue

        # Skip stickied posts
        if post.get("stickied"):
            continue

        results.append({
            "title": title,
            "url": f"https://reddit.com{post.get('permalink','')}",
            "external_url": post.get("url_overridden_by_dest", "") or post.get("url", ""),
            "hotness": post.get("score", 0),
            "posted_ts": created,
            "desc": f"{post.get('num_comments', 0)} comments, u/{post.get('author','?')}",
            "selftext": (post.get("selftext") or "")[:200],
        })

    return results


def fetch_all(subs=None) -> list:
    if subs is None:
        subs = SUBREDDITS

    all_items = []
    for sub_id, sub_name, direction in subs:
        items = fetch_subreddit(sub_id)
        for it in items:
            it["source"] = sub_name
            it["source_id"] = f"reddit_{sub_id}"
            it["direction"] = direction
        all_items.extend(items)
        print(f"  ✅ {sub_name}: {len(items)} 条")
        time.sleep(0.5)  # Reddit rate limit

    return all_items


if __name__ == "__main__":
    items = fetch_all()
    print(f"\n总共 {len(items)} 条 Reddit 24h 内")
    for it in items[:5]:
        print(f"  [{it['source']}] {it['title'][:60]} (score={it['hotness']})")
