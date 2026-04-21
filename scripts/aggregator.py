"""聚合所有源的热点，去重，过滤 24h 内的项。"""
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from sources import dailyhot, hackernews, reddit, rss


def _dedupe(items):
    """按 title 近似去重（归一化后相同就算一条）。"""
    seen = {}
    for it in items:
        key = _normalize_title(it["title"])
        if key in seen:
            # 保留热度高的那条
            if it["hotness"] > seen[key]["hotness"]:
                seen[key] = it
        else:
            seen[key] = it
    return list(seen.values())


def _normalize_title(title: str) -> str:
    import re
    s = title.lower()
    # 去掉标点、空格、emoji 的大部分噪音
    s = re.sub(r"[\s\-_·|:：,，.。!?、\(\)\[\]【】《》\"']+", "", s)
    # 取前 40 个字符做 key
    return s[:40]


def fetch_all(timeout_per_source: int = 60) -> list:
    """并行抓所有源。"""
    results = []

    def run(func, name):
        try:
            t = time.time()
            print(f"\n📡 抓 {name}...")
            items = func()
            dt = time.time() - t
            print(f"   {name} 完成: {len(items)} 条 ({dt:.1f}s)")
            return items
        except Exception as e:
            print(f"   ❌ {name} 失败: {e}")
            return []

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            ex.submit(run, dailyhot.fetch_all, "中文聚合"): "dailyhot",
            ex.submit(run, hackernews.fetch, "HackerNews"): "hn",
            ex.submit(run, reddit.fetch_all, "Reddit"): "reddit",
            ex.submit(run, rss.fetch_all, "RSS (BBC/CNN/TechCrunch...)"): "rss",
        }
        for f in futures:
            try:
                results.extend(f.result(timeout=timeout_per_source * 2))
            except Exception as e:
                print(f"  ⚠️ {futures[f]} timeout: {e}")

    # 去重
    before = len(results)
    results = _dedupe(results)
    print(f"\n🔀 去重: {before} → {len(results)}")

    # 按 24h 过滤
    now = int(time.time())
    cutoff = now - 24 * 3600
    results = [r for r in results if r.get("posted_ts", now) >= cutoff]
    print(f"⏰ 24h 内: {len(results)} 条")

    return results


def filter_by_direction(items, direction: str):
    """按方向过滤（AI / 美国 / 世界 / 中国）。"""
    if not direction or direction == "all":
        return items
    return [it for it in items if it.get("direction", "") == direction]


if __name__ == "__main__":
    items = fetch_all()
    print(f"\n=== 按方向分布 ===")
    from collections import Counter
    c = Counter(it.get("direction", "?") for it in items)
    for d, n in c.most_common():
        print(f"  {d}: {n}")

    print(f"\n=== 热度 Top 10 ===")
    top = sorted(items, key=lambda x: -x.get("hotness", 0))[:10]
    for i, it in enumerate(top, 1):
        print(f"  {i}. [{it['source']}] {it['title'][:60]} (hot={it['hotness']})")
