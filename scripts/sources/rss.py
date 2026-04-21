"""RSS feeds - 国际通讯社 / AI 博客。"""
import feedparser
import time
from datetime import datetime

FEEDS = [
    # 世界新闻（Reuters/BBC 没有公开 RSS，用这些替代）
    ("http://feeds.bbci.co.uk/news/world/rss.xml",       "BBC World", "世界"),
    ("https://www.aljazeera.com/xml/rss/all.xml",         "Al Jazeera", "世界"),
    ("https://www.theguardian.com/world/rss",             "Guardian World", "世界"),

    # 美国本土
    ("https://www.theguardian.com/us-news/rss",           "Guardian US", "美国"),
    ("http://rss.cnn.com/rss/cnn_us.rss",                 "CNN US", "美国"),

    # AI / 科技
    ("https://techcrunch.com/feed/",                      "TechCrunch", "AI"),
    ("https://www.theverge.com/rss/index.xml",            "The Verge", "AI"),
    ("https://venturebeat.com/category/ai/feed/",         "VentureBeat AI", "AI"),
]


def _parse_date(entry) -> int:
    """从 feedparser entry 解析时间戳。"""
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, field, None)
        if t:
            try:
                return int(time.mktime(t))
            except Exception:
                pass
    return int(time.time())


def fetch_feed(url: str, limit: int = 20, timeout: int = 15) -> list:
    """抓一个 RSS feed，返回 24h 内的项。"""
    try:
        # feedparser 内部会请求，timeout 通过 socket 默认控制
        import socket
        socket.setdefaulttimeout(timeout)
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"  ⚠️ RSS 失败 {url}: {e}")
        return []

    now = int(time.time())
    cutoff_24h = now - 24 * 3600
    results = []

    for entry in feed.entries[:limit]:
        title = (entry.get("title") or "").strip()
        if not title:
            continue

        posted_ts = _parse_date(entry)
        if posted_ts < cutoff_24h:
            continue

        # 用 summary 或 description 作为描述
        desc = (entry.get("summary") or entry.get("description") or "")[:200]

        results.append({
            "title": title,
            "url": entry.get("link", ""),
            "hotness": 50,  # RSS 没有热度，给默认值
            "posted_ts": posted_ts,
            "desc": desc,
        })

    return results


def fetch_all(feeds=None) -> list:
    if feeds is None:
        feeds = FEEDS

    all_items = []
    for url, name, direction in feeds:
        items = fetch_feed(url)
        for it in items:
            it["source"] = name
            it["source_id"] = f"rss_{name.lower().replace(' ', '_')}"
            it["direction"] = direction
        all_items.extend(items)
        print(f"  ✅ {name}: {len(items)} 条")

    return all_items


if __name__ == "__main__":
    items = fetch_all()
    print(f"\n总共 {len(items)} 条 RSS 24h 内")
    for it in items[:5]:
        print(f"  [{it['source']}] {it['title'][:60]}")
