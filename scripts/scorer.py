"""用 MiniMax M2.7 批量给热点打分 + 生成选题角度。

策略:
1. 先用规则过滤一轮（避免烧钱：娱乐八卦类、情感类评分低）
2. 批量喂给 MiniMax（一次 20-30 条），让它打分 + 生成角度
3. 解析 JSON 返回
"""
import json
import os
import re
import urllib.request
import urllib.error
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


MINIMAX_BASE_URL = "https://api.minimaxi.com/v1"
# 用 highspeed 变种，不容易被限流（standard 版本经常 529）
MINIMAX_MODEL = "MiniMax-M2.7-highspeed"

# Ollama 本地备用
OLLAMA_BASE_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:35b-a3b")

# 后端选择: "minimax" 或 "ollama"。环境变量 SCOUT_BACKEND 可覆盖
BACKEND = os.environ.get("SCOUT_BACKEND", "minimax").lower()


def _load_minimax_key() -> str:
    # Priority: env → openclaw.json
    key = os.environ.get("MINIMAX_API_KEY", "")
    if key:
        return key
    try:
        with open(os.path.expanduser("~/.openclaw/openclaw.json")) as f:
            cfg = json.load(f)
        return cfg.get("env", {}).get("MINIMAX_API_KEY", "")
    except Exception:
        return ""


def _call_minimax(system: str, user: str, max_tokens: int = 4096,
                  temperature: float = 0.4, timeout: int = 90,
                  max_retries: int = 4) -> str:
    """调用 MiniMax chat completions API，带 529/429 重试。"""
    api_key = _load_minimax_key()
    if not api_key:
        raise RuntimeError("MINIMAX_API_KEY 未配置")

    url = f"{MINIMAX_BASE_URL}/chat/completions"
    payload = json.dumps({
        "model": MINIMAX_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()

    last_err = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=payload, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            choices = data.get("choices", [])
            if not choices:
                return ""
            content = choices[0].get("message", {}).get("content", "").strip()
            return _strip_thinking(content)
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 529, 503):
                # 限流/过载 - 指数退避
                wait = (2 ** attempt) * 3  # 3, 6, 12, 24 秒
                print(f"    ⏳ HTTP {e.code}，等 {wait}s 后重试 (尝试 {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            # 其他错误不重试
            raise
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise

    raise RuntimeError(f"MiniMax 重试 {max_retries} 次后仍失败: {last_err}")


def _strip_thinking(text: str) -> str:
    """去掉 <think>...</think> 块。"""
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()


def _call_ollama(system: str, user: str, max_tokens: int = 4096,
                 temperature: float = 0.4, timeout: int = 300) -> str:
    """调用本地 Ollama (Qwen/Gemma)。"""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "think": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }).encode()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    content = data.get("message", {}).get("content", "").strip()
    return _strip_thinking(content)


def _call_ai(system: str, user: str, **kwargs) -> str:
    """统一入口，按 BACKEND 派发。"""
    if BACKEND == "ollama":
        return _call_ollama(system, user, **kwargs)
    return _call_minimax(system, user, **kwargs)


# ===== Pre-filter rules =====

SKIP_KEYWORDS = [
    # 娱乐八卦 - 不做视频
    "综艺", "明星", "绯闻", "恋情", "分手", "离婚", "出轨",
    # 游戏
    "崩坏", "原神", "王者荣耀", "lol", "dota",
    # 太小众
]

LOW_VALUE_PATTERNS = [
    r"^(图片|\[图\]|GIF|.gif)",
    r"广告|推广|福利|抽奖",
]


def _prefilter(items: list) -> list:
    """简单规则过滤，省 AI 调用。"""
    results = []
    for it in items:
        title = it.get("title", "")
        # 跳过明显的娱乐八卦
        if any(kw in title for kw in SKIP_KEYWORDS):
            continue
        if any(re.search(p, title, re.I) for p in LOW_VALUE_PATTERNS):
            continue
        # 保留
        results.append(it)
    return results


# ===== AI scoring =====

SCORING_SYSTEM = """你是短视频选题策划专家。用户会给你一批新闻/热榜条目，你要评估每条的短视频潜力。

评分维度（每项 0-10）:
- topicality: 话题性（有多少人关心、会不会讨论）
- visual_impact: 视觉冲击力（能不能拍出吸引眼球的画面）
- viral_potential: 病毒传播潜力（会不会被转发、模仿）

特别偏好：
- AI、科技突破（给高分）
- 美国本土重大事件（给高分）
- 国际大事件、战争、地缘冲突（给高分）
- 娱乐八卦、鸡汤、软文（给低分）
- 太冷门技术细节（给低分）

对每条，你还要生成：
- angles: 3 个视频切入角度（每个一句话，具体可拍）
- keywords: 2-3 个 hashtag（英文，带 #）
- suggested_duration_sec: 建议时长（30/45/60/90）
- mood: 基调（energetic/serious/funny/mysterious/shocking）

返回**纯 JSON 数组**，每条对应一个输入条目，不要加 ```json``` 标记。
格式:
[{"idx":0,"topicality":8,"visual_impact":7,"viral_potential":9,"angles":["角度1","角度2","角度3"],"keywords":["#AI","#Tech"],"suggested_duration_sec":45,"mood":"energetic"}]
"""


def _score_batch(batch: list, timeout: int = 90) -> list:
    """一次打分一批（通常 20-30 条）。返回 scores 列表，和 batch 一一对应。"""
    lines = []
    for i, it in enumerate(batch):
        title = it["title"]
        source = it["source"]
        direction = it.get("direction", "?")
        desc = it.get("desc", "")[:100]
        lines.append(f"[{i}] 方向={direction} 来源={source} | {title}"
                     + (f" | {desc}" if desc else ""))

    user_prompt = "给以下 {n} 条打分:\n\n{lines}\n\n返回 JSON 数组（长度 {n}）。".format(
        n=len(batch), lines="\n".join(lines)
    )

    try:
        raw = _call_ai(SCORING_SYSTEM, user_prompt, max_tokens=6000, timeout=timeout)
    except Exception as e:
        print(f"  ⚠️ 批量打分失败: {e}")
        return [_fallback_score() for _ in batch]

    # 解析 JSON
    scores = _parse_scores_json(raw, len(batch))
    return scores


def _parse_scores_json(raw: str, expected_len: int) -> list:
    """尝试从 AI 输出里抠出 JSON 数组。"""
    # 去掉可能的 ```json``` 包裹
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    # 尝试找 [...] 的范围
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end < start:
        print(f"  ⚠️ JSON 解析失败，原始输出前200字: {raw[:200]}")
        return [_fallback_score() for _ in range(expected_len)]

    try:
        arr = json.loads(raw[start:end+1])
    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON 格式错误: {e}")
        return [_fallback_score() for _ in range(expected_len)]

    # 按 idx 对齐
    result = [_fallback_score() for _ in range(expected_len)]
    for item in arr:
        if not isinstance(item, dict):
            continue
        idx = item.get("idx")
        if isinstance(idx, int) and 0 <= idx < expected_len:
            result[idx] = _normalize_score(item)
    return result


def _fallback_score():
    return {
        "topicality": 5,
        "visual_impact": 5,
        "viral_potential": 5,
        "angles": [],
        "keywords": [],
        "suggested_duration_sec": 45,
        "mood": "energetic",
        "_fallback": True,
    }


def _normalize_score(s: dict) -> dict:
    def _clip(v, lo=0, hi=10):
        try:
            return max(lo, min(hi, int(v)))
        except (ValueError, TypeError):
            return 5
    return {
        "topicality": _clip(s.get("topicality", 5)),
        "visual_impact": _clip(s.get("visual_impact", 5)),
        "viral_potential": _clip(s.get("viral_potential", 5)),
        "angles": (s.get("angles") or [])[:3],
        "keywords": (s.get("keywords") or [])[:3],
        "suggested_duration_sec": int(s.get("suggested_duration_sec", 45)),
        "mood": s.get("mood", "energetic"),
    }


def score_all(items: list, batch_size: int = 15, max_items: int = 60,
              parallel: int = 4) -> list:
    """批量打分。为省成本只打前 max_items 条（按 hotness 排序）。"""
    # 先 prefilter
    before = len(items)
    items = _prefilter(items)
    print(f"  🧹 规则过滤: {before} → {len(items)}")

    # 按热度排序，只评分 top N
    items_sorted = sorted(items, key=lambda x: -x.get("hotness", 0))
    subset = items_sorted[:max_items]
    print(f"  🎯 取 Top {len(subset)} 条送去 AI 评分")

    # 分批
    batches = [subset[i:i+batch_size] for i in range(0, len(subset), batch_size)]
    print(f"  📦 分 {len(batches)} 批并行打分...")

    scores = [None] * len(subset)

    def score_one_batch(batch_idx, batch):
        t = time.time()
        s = _score_batch(batch)
        print(f"    ✅ 批 {batch_idx+1}/{len(batches)} 完成 ({time.time()-t:.1f}s)")
        return batch_idx, s

    with ThreadPoolExecutor(max_workers=parallel) as ex:
        futures = [ex.submit(score_one_batch, i, b) for i, b in enumerate(batches)]
        for f in as_completed(futures):
            batch_idx, s = f.result()
            for i, score in enumerate(s):
                scores[batch_idx * batch_size + i] = score

    # 把 score 合并到 item 里
    for item, score in zip(subset, scores):
        if score is None:
            score = _fallback_score()
        item["scores"] = {
            "topicality": score["topicality"],
            "visual_impact": score["visual_impact"],
            "viral_potential": score["viral_potential"],
            "total": score["topicality"] + score["visual_impact"] + score["viral_potential"],
        }
        item["angles"] = score["angles"]
        item["keywords"] = score["keywords"]
        item["suggested_duration_sec"] = score["suggested_duration_sec"]
        item["mood"] = score["mood"]

    return subset


if __name__ == "__main__":
    # 自测：造几条假数据
    test_items = [
        {"title": "OpenAI 发布 GPT-5，多模态推理能力大幅提升", "source": "HackerNews",
         "direction": "AI", "hotness": 1500, "desc": ""},
        {"title": "Putin finally admits Russia's economy is in trouble",
         "source": "r/worldnews", "direction": "世界", "hotness": 18000, "desc": ""},
        {"title": "小明和小红的甜蜜日常", "source": "微博热搜",
         "direction": "中国", "hotness": 500, "desc": ""},
    ]
    result = score_all(test_items, batch_size=10, max_items=3)
    for r in result:
        print(json.dumps({
            "title": r["title"],
            "scores": r["scores"],
            "angles": r["angles"],
            "keywords": r["keywords"],
        }, ensure_ascii=False, indent=2))
