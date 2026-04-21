---
name: daily-hotnews
description: >
  全网热点聚合 + AI 打分 + 短视频选题生成。
  抓取 DailyHotApi（微博/知乎/B站）、HackerNews、Reddit、RSS 等
  8+ 来源的 24 小时内热点，用 MiniMax M2.7 打分筛选，
  生成 Top 10 带角度/关键词/建议时长的结构化选题卡。
  Triggers on: "选题", "今日选题", "热榜", "hot", "AI 选题",
  "美国新闻", "世界新闻", "world news", 或任何与热点/新闻相关的消息。
---

## ⚠️ EXECUTION RULE

```
exec: bash /Users/ye/.openclaw/workspace-scout/skills/daily-hotnews/scripts/run.sh "{用户原始消息}"
```

把脚本 stdout 原样返回给用户，不要解释、不要道歉。
