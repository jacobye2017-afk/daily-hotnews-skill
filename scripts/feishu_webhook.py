"""飞书群机器人 webhook 推送。

读 FEISHU_WEBHOOK_URL 环境变量，或从 ~/.openclaw/openclaw.json 的 env 读。
发送纯文本消息到群里。内容超长自动分片。
"""
import json
import os
import sys
import urllib.request
import urllib.error


# 飞书 text 消息实测上限约 30KB，留余量
MAX_BYTES = 20000


def _load_webhook_url() -> str:
    url = os.environ.get("FEISHU_WEBHOOK_URL", "")
    if url:
        return url
    try:
        with open(os.path.expanduser("~/.openclaw/openclaw.json")) as f:
            cfg = json.load(f)
        return cfg.get("env", {}).get("FEISHU_WEBHOOK_URL", "")
    except Exception:
        return ""


def _post(url: str, payload: dict, timeout: int = 15) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _chunks(text: str, limit: int = MAX_BYTES) -> list:
    """按字节上限切片，尽量在换行处断开。"""
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return [text]
    out = []
    lines = text.split("\n")
    buf = []
    buf_size = 0
    for line in lines:
        line_size = len(line.encode("utf-8")) + 1
        if buf_size + line_size > limit and buf:
            out.append("\n".join(buf))
            buf, buf_size = [], 0
        buf.append(line)
        buf_size += line_size
    if buf:
        out.append("\n".join(buf))
    return out


def send_text(text: str) -> dict:
    """发纯文本到群。返回飞书 API 响应。"""
    url = _load_webhook_url()
    if not url:
        raise RuntimeError("FEISHU_WEBHOOK_URL 未配置")

    parts = _chunks(text)
    last_resp = {}
    for i, part in enumerate(parts):
        prefix = f"【{i+1}/{len(parts)}】\n" if len(parts) > 1 else ""
        payload = {
            "msg_type": "text",
            "content": {"text": prefix + part},
        }
        last_resp = _post(url, payload)
        if last_resp.get("code", 0) != 0:
            raise RuntimeError(f"飞书返回错误: {last_resp}")
    return last_resp


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "🧪 webhook 连通测试"
    resp = send_text(msg)
    print(json.dumps(resp, ensure_ascii=False))
