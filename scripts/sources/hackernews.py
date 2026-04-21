"""HackerNews top/new stories - AI 技术最新动态。

使用官方 Firebase API: https://github.com/HackerNews/API
"""
import requests
import time

TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


def fetch(limit: int = 30, timeout: int = 10) -> list:
    """抓 HackerNews top stories。"""
    try:
        resp = requests.get(TOP_URL, timeout=timeout)
        resp.raise_for_status()
        ids = resp.json()[:limit]
    except Exception as e:
        print(f"  ⚠️ HackerNews 列表失败: {e}")
        return []

    now = int(time.time())
    cutoff_24h = now - 24 * 3600
    results = []

    for item_id in ids:
        try:
            r = requests.get(ITEM_URL.format(id=item_id), timeout=5)
            item = r.json()
        except Exception:
            continue

        if not item or item.get("type") != "story":
            continue

        title = (item.get("title") or "").strip()
        if not title:
            continue

        posted_ts = item.get("time", now)
        # 只要 24h 内的
        if posted_ts < cutoff_24h:
            continue

        results.append({
            "title": title,
            "url": item.get("url") or f"https://news.ycombinator.com/item?id={item_id}",
            "hotness": item.get("score", 0),
            "posted_ts": posted_ts,
            "desc": f"by {item.get('by', '?')}, {item.get('descendants', 0)} comments",
            "source": "HackerNews",
            "source_id": "hackernews",
            "direction": "AI",
        })

    return results


if __name__ == "__main__":
    items = fetch()
    print(f"HackerNews: {len(items)} 条 24h 内的")
    for it in items[:5]:
        print(f"  • {it['title'][:60]} (score={it['hotness']})")
