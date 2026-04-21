---
name: daily-hotnews
description: >
  全网热点聚合 + AI 打分 + 短视频选题生成。
  抓取 DailyHotApi（微博/知乎/B站）、HackerNews、Reddit、RSS 等
  8+ 来源的 24 小时内热点，用 MiniMax M2.7 打分筛选，
  生成 Top 10 带角度/关键词/建议时长的结构化选题卡。
  脚本会**直接通过飞书 webhook 推送完整报告到群**，agent 只需回复简短状态。
  Triggers on: "选题", "今日选题", "热榜", "hot", "AI 选题",
  "美国新闻", "世界新闻", "world news", 或任何与热点/新闻相关的消息。
---

## 执行

```
exec: bash /Users/ye/.openclaw/workspace-scout/skills/daily-hotnews/scripts/run.sh "{用户原始消息}"
```

## 返回

把脚本 stdout **原样**返回给用户。stdout 通常只有一行（类似 `✅ 已推送 Top 10 条选题到群组`），因为完整报告已经通过 webhook 直接发到群里了。

不要补充、翻译、解释。就那一行。
