"""推送去重：记住过去 24h 已推过的 URL，避免重复。

状态文件: ~/.openclaw/workspace-scout/state/pushed_urls.json
格式: {url: unix_ts_first_pushed}
TTL: 24 小时，自动清理过期记录。
"""
import json
import os
import time


STATE_DIR = os.path.expanduser("~/.openclaw/workspace-scout/state")
STATE_FILE = os.path.join(STATE_DIR, "pushed_urls.json")
TTL_SECONDS = 24 * 3600


def _load() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save(state: dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def _prune(state: dict) -> dict:
    cutoff = time.time() - TTL_SECONDS
    return {url: ts for url, ts in state.items() if ts >= cutoff}


def filter_new(items: list) -> tuple:
    """过滤掉已在 24h 记忆内的 URL。返回 (新条目, 跳过数)。"""
    state = _prune(_load())
    _save(state)  # 顺便落盘清理后的
    seen = set(state.keys())
    new_items = []
    skipped = 0
    for it in items:
        url = it.get("url", "")
        if url and url in seen:
            skipped += 1
            continue
        new_items.append(it)
    return new_items, skipped


def mark_pushed(urls):
    """把本次实际推送的 URL 加入记忆。"""
    state = _prune(_load())
    now = time.time()
    for url in urls:
        if url and url not in state:
            state[url] = now
    _save(state)


def stats() -> dict:
    state = _prune(_load())
    return {
        "total_remembered": len(state),
        "oldest_age_hours": round((time.time() - min(state.values())) / 3600, 1) if state else 0,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        _save({})
        print("✓ 已清空记忆")
    else:
        print(json.dumps(stats(), indent=2))
