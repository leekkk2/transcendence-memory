#!/usr/bin/env python3
"""批量入库脚本 — 零外部依赖，只用 Python 标准库。

用法：
  python3 batch-ingest.py <endpoint> <api-key> <container> <input-file>

输入文件格式（JSONL，每行一个 JSON 对象）：
  {"id":"mem-001","text":"记忆内容","tags":["tag1"]}
  {"id":"mem-002","text":"另一条记忆","source":"telegram"}

功能：
  - 分批发送（默认每批 50 条）
  - 失败自动重试（最多 3 次）
  - 进度输出
  - 支持大文件流式读取
"""

import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BATCH_SIZE = 50
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒


def send_batch(endpoint: str, api_key: str, container: str,
               objects: list[dict], retry: int = 0) -> dict:
    url = f"{endpoint}/ingest-memory/objects"
    payload = json.dumps({"container": container, "objects": objects, "auto_embed": False}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError) as e:
        if retry < MAX_RETRIES:
            print(f"  重试 {retry + 1}/{MAX_RETRIES}（{e}）")
            time.sleep(RETRY_DELAY * (retry + 1))
            return send_batch(endpoint, api_key, container, objects, retry + 1)
        raise


def main() -> None:
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)

    endpoint = sys.argv[1].rstrip("/")
    api_key = sys.argv[2]
    container = sys.argv[3]
    input_file = Path(sys.argv[4])

    if not input_file.exists():
        print(f"文件不存在：{input_file}")
        sys.exit(1)

    # 流式读取 JSONL
    batch: list[dict] = []
    total_sent = 0
    total_accepted = 0

    with open(input_file, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  跳过第 {line_no} 行（JSON 解析失败：{e}）")
                continue

            batch.append(obj)

            if len(batch) >= BATCH_SIZE:
                result = send_batch(endpoint, api_key, container, batch)
                accepted = result.get("accepted", 0)
                total_sent += len(batch)
                total_accepted += accepted
                print(f"  已发送 {total_sent} 条，已接受 {total_accepted} 条")
                batch = []

    # 发送剩余
    if batch:
        result = send_batch(endpoint, api_key, container, batch)
        accepted = result.get("accepted", 0)
        total_sent += len(batch)
        total_accepted += accepted

    print(f"\n完成：发送 {total_sent} 条，接受 {total_accepted} 条")
    print(f"提示：运行 /embed 刷新索引以使新记忆可检索")


if __name__ == "__main__":
    main()
