#!/usr/bin/env python3
"""批量入库脚本 — 零外部依赖，只用 Python 标准库。

用法：
  python3 batch-ingest.py <endpoint> <api-key> <container> <input-file> [选项]

选项：
  --max-bytes N     单批最大字节数（默认 512000，即 500 KB）
  --batch-size N    单批最大条数（默认 50）
  --redact          入库前对常见敏感信息做脱敏
  --probe           入库前先探测 /ingest-memory/contract
  --resume          跳过上次已成功的行（基于进度文件）
  --failed-log F    失败对象写入指定文件（默认 <input>.failed.jsonl）

输入文件格式（JSONL，每行一个 JSON 对象）：
  {"id":"mem-001","text":"记忆内容","tags":["tag1"]}
  {"id":"mem-002","text":"另一条记忆","source":"telegram"}
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ── 默认参数 ──────────────────────────────────────────────
DEFAULT_BATCH_SIZE = 50
DEFAULT_MAX_BYTES = 512_000  # 500 KB
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒
MIN_BATCH_SIZE = 1  # 413 自动缩批下限

# ── WAF 兼容请求头 ────────────────────────────────────────
# 许多部署在 Cloudflare/WAF 后面的服务会拦截默认 urllib User-Agent
# 参考：反馈问题 1 — urllib 默认头触发 Cloudflare error 1010
REQUEST_HEADERS_BASE = {
    "Content-Type": "application/json",
    "User-Agent": "transcendence-memory-batch/0.2",
    "Accept": "application/json, text/plain, */*",
}

# ── 脱敏正则 ──────────────────────────────────────────────
# 覆盖常见 API key / token / 私钥模式
_REDACT_PATTERNS: list[tuple[re.Pattern, str]] = [
    # 通用 key=value / key: value 格式（长度 >=20 的值）
    (re.compile(
        r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|refresh[_-]?token'
        r'|auth[_-]?token|bearer|password|passwd|credential'
        r'|client[_-]?secret|private[_-]?key|signing[_-]?key'
        r'|x[_-]api[_-]key)'
        r'[\s]*[=:"\s]+[\s"]*([A-Za-z0-9_\-/.+]{20,})'
    ), r'\1=<REDACTED>'),
    # OpenAI sk-...
    (re.compile(r'sk-[A-Za-z0-9]{20,}'), '<REDACTED-OPENAI-KEY>'),
    # GitHub ghp_ / gho_ / ghs_ / ghr_
    (re.compile(r'gh[psohr]_[A-Za-z0-9]{36,}'), '<REDACTED-GITHUB-TOKEN>'),
    # Google AIza...
    (re.compile(r'AIza[A-Za-z0-9_\-]{35}'), '<REDACTED-GOOGLE-KEY>'),
    # AWS AKIA...
    (re.compile(r'AKIA[A-Z0-9]{16}'), '<REDACTED-AWS-KEY>'),
    # Slack xoxb- / xoxp- / xoxs-
    (re.compile(r'xox[bpsa]-[A-Za-z0-9\-]{10,}'), '<REDACTED-SLACK-TOKEN>'),
    # Telegram bot token
    (re.compile(r'\b\d{8,10}:[A-Za-z0-9_\-]{35}\b'), '<REDACTED-TG-TOKEN>'),
    # PEM 私钥块
    (re.compile(
        r'-----BEGIN\s+(RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----'
        r'[\s\S]*?'
        r'-----END\s+(RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----',
        re.MULTILINE,
    ), '<REDACTED-PRIVATE-KEY>'),
    # Bearer token in headers
    (re.compile(r'(?i)(Authorization:\s*Bearer\s+)[A-Za-z0-9_\-/.+]{20,}'),
     r'\1<REDACTED>'),
    # .env 风格 KEY=value（至少 16 字符的值）
    (re.compile(r'^([A-Z_]{4,}_(?:KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL))\s*=\s*\S{16,}',
                re.MULTILINE),
     r'\1=<REDACTED>'),
]


def redact_text(text: str) -> str:
    """对文本中的常见敏感信息做正则脱敏。"""
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def probe_contract(endpoint: str, api_key: str) -> dict | None:
    """探测 /ingest-memory/contract，返回接口 schema 信息。"""
    url = f"{endpoint}/ingest-memory/contract"
    req = urllib.request.Request(
        url,
        headers={**REQUEST_HEADERS_BASE, "X-API-KEY": api_key},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            print(f"[探测] contract 响应: {json.dumps(data, ensure_ascii=False)[:500]}")
            return data
    except Exception as e:
        print(f"[探测] contract 请求失败: {e}")
        print("[探测] 继续执行，但可能遇到 422 校验错误")
        return None


def send_batch(endpoint: str, api_key: str, container: str,
               objects: list[dict]) -> dict:
    """发送一批对象到 /ingest-memory/objects。

    - 使用 WAF 兼容请求头
    - 网络错误自动重试
    - 413 时自动对半缩批递归重试
    """
    url = f"{endpoint}/ingest-memory/objects"
    payload = json.dumps(
        {"container": container, "objects": objects, "auto_embed": False},
        ensure_ascii=False,
    ).encode("utf-8")

    headers = {**REQUEST_HEADERS_BASE, "X-API-KEY": api_key}
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 413:
                # 请求体过大 — 自动对半缩批重试
                return _split_and_retry(endpoint, api_key, container, objects)
            if e.code == 422:
                # 校验失败 — 记录响应体便于排查
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="replace")[:1000]
                except Exception:
                    pass
                print(f"  [422] 校验失败: {body}")
                raise
            last_error = e
            if attempt < MAX_RETRIES:
                print(f"  重试 {attempt + 1}/{MAX_RETRIES}（HTTP {e.code}）")
                time.sleep(RETRY_DELAY * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                print(f"  重试 {attempt + 1}/{MAX_RETRIES}（{e}）")
                time.sleep(RETRY_DELAY * (attempt + 1))

    raise last_error  # type: ignore[misc]


def _split_and_retry(endpoint: str, api_key: str, container: str,
                     objects: list[dict]) -> dict:
    """413 时将批次对半拆分并递归重试。"""
    if len(objects) <= MIN_BATCH_SIZE:
        # 单条对象仍然 413 — 可能是单条内容过大
        obj_id = objects[0].get("id", "?")
        text_len = len(objects[0].get("text", ""))
        print(f"  [413] 单条对象 {obj_id} 仍然过大（text 长度 {text_len}），跳过")
        return {"accepted": 0, "skipped_413": [obj_id]}

    mid = len(objects) // 2
    print(f"  [413] 批次过大（{len(objects)} 条），拆为 {mid} + {len(objects) - mid} 重试")
    r1 = send_batch(endpoint, api_key, container, objects[:mid])
    r2 = send_batch(endpoint, api_key, container, objects[mid:])

    accepted = r1.get("accepted", 0) + r2.get("accepted", 0)
    skipped = r1.get("skipped_413", []) + r2.get("skipped_413", [])
    result = {"accepted": accepted}
    if skipped:
        result["skipped_413"] = skipped
    return result


def load_progress(progress_file: Path) -> int:
    """读取上次成功处理到的行号。"""
    if progress_file.exists():
        try:
            return int(progress_file.read_text().strip())
        except (ValueError, OSError):
            pass
    return 0


def save_progress(progress_file: Path, line_no: int) -> None:
    """保存当前处理进度。"""
    try:
        progress_file.write_text(str(line_no))
    except OSError:
        pass


def estimate_payload_bytes(objects: list[dict]) -> int:
    """估算批次 JSON payload 大小（字节）。"""
    # 粗略估算：对象列表的 JSON 序列化 + 外层结构开销
    return sum(len(json.dumps(o, ensure_ascii=False).encode("utf-8")) for o in objects) + 100


def parse_args(argv: list[str]) -> dict:
    """解析命令行参数。"""
    if len(argv) < 5:
        print(__doc__)
        sys.exit(1)

    opts: dict = {
        "endpoint": argv[1].rstrip("/"),
        "api_key": argv[2],
        "container": argv[3],
        "input_file": Path(argv[4]),
        "max_bytes": DEFAULT_MAX_BYTES,
        "batch_size": DEFAULT_BATCH_SIZE,
        "redact": False,
        "probe": False,
        "resume": False,
        "failed_log": None,
    }

    i = 5
    while i < len(argv):
        arg = argv[i]
        if arg == "--max-bytes" and i + 1 < len(argv):
            opts["max_bytes"] = int(argv[i + 1])
            i += 2
        elif arg == "--batch-size" and i + 1 < len(argv):
            opts["batch_size"] = int(argv[i + 1])
            i += 2
        elif arg == "--redact":
            opts["redact"] = True
            i += 1
        elif arg == "--probe":
            opts["probe"] = True
            i += 1
        elif arg == "--resume":
            opts["resume"] = True
            i += 1
        elif arg == "--failed-log" and i + 1 < len(argv):
            opts["failed_log"] = Path(argv[i + 1])
            i += 2
        else:
            print(f"未知参数: {arg}")
            print(__doc__)
            sys.exit(1)

    if not opts["input_file"].exists():
        print(f"文件不存在: {opts['input_file']}")
        sys.exit(1)

    if opts["failed_log"] is None:
        opts["failed_log"] = Path(str(opts["input_file"]) + ".failed.jsonl")

    return opts


def main() -> None:
    opts = parse_args(sys.argv)
    endpoint: str = opts["endpoint"]
    api_key: str = opts["api_key"]
    container: str = opts["container"]
    input_file: Path = opts["input_file"]
    max_bytes: int = opts["max_bytes"]
    batch_size: int = opts["batch_size"]
    do_redact: bool = opts["redact"]
    do_probe: bool = opts["probe"]
    do_resume: bool = opts["resume"]
    failed_log: Path = opts["failed_log"]

    # ── contract 探测 ─────────────────────────────────────
    if do_probe:
        probe_contract(endpoint, api_key)

    # ── 断点续传 ──────────────────────────────────────────
    progress_file = Path(str(input_file) + ".progress")
    start_line = load_progress(progress_file) if do_resume else 0
    if start_line > 0:
        print(f"[续传] 从第 {start_line + 1} 行开始")

    # ── 流式读取 JSONL ────────────────────────────────────
    batch: list[dict] = []
    batch_bytes = 0
    total_sent = 0
    total_accepted = 0
    total_skipped = 0
    failed_ids: list[str] = []

    failed_fh = None
    if failed_log:
        try:
            failed_fh = open(failed_log, "a", encoding="utf-8")
        except OSError as e:
            print(f"[警告] 无法打开失败日志 {failed_log}: {e}")

    try:
        with open(input_file, encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                # 断点续传：跳过已处理行
                if line_no <= start_line:
                    continue

                line = line.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"  跳过第 {line_no} 行（JSON 解析失败: {e}）")
                    continue

                # 脱敏处理
                if do_redact and "text" in obj:
                    obj["text"] = redact_text(obj["text"])

                obj_bytes = len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

                # 检查是否需要发送当前批次（条数或字节数达到上限）
                if batch and (len(batch) >= batch_size
                              or batch_bytes + obj_bytes > max_bytes):
                    result = _send_and_record(
                        endpoint, api_key, container, batch,
                        failed_fh, failed_ids,
                    )
                    total_sent += len(batch)
                    total_accepted += result.get("accepted", 0)
                    total_skipped += len(result.get("skipped_413", []))
                    print(f"  已发送 {total_sent} 条，已接受 {total_accepted} 条")
                    batch = []
                    batch_bytes = 0
                    save_progress(progress_file, line_no - 1)

                batch.append(obj)
                batch_bytes += obj_bytes

        # 发送剩余
        if batch:
            result = _send_and_record(
                endpoint, api_key, container, batch,
                failed_fh, failed_ids,
            )
            total_sent += len(batch)
            total_accepted += result.get("accepted", 0)
            total_skipped += len(result.get("skipped_413", []))

    finally:
        if failed_fh:
            failed_fh.close()

    # 完成后清理进度文件
    if progress_file.exists():
        try:
            progress_file.unlink()
        except OSError:
            pass

    print(f"\n完成: 发送 {total_sent} 条，接受 {total_accepted} 条")
    if total_skipped:
        print(f"  跳过（413 过大）: {total_skipped} 条")
    if failed_ids:
        print(f"  失败: {len(failed_ids)} 条，详见 {failed_log}")
    print("提示: 运行 /embed 刷新索引以使新记忆可检索")


def _send_and_record(endpoint: str, api_key: str, container: str,
                     batch: list[dict],
                     failed_fh, failed_ids: list[str]) -> dict:
    """发送批次并记录失败对象。"""
    try:
        result = send_batch(endpoint, api_key, container, batch)
        # 记录因 413 跳过的对象
        for obj_id in result.get("skipped_413", []):
            failed_ids.append(obj_id)
            if failed_fh:
                for obj in batch:
                    if obj.get("id") == obj_id:
                        failed_fh.write(json.dumps(
                            {"id": obj_id, "reason": "413_too_large"},
                            ensure_ascii=False,
                        ) + "\n")
                        break
        return result
    except Exception as e:
        print(f"  批次失败: {e}")
        # 记录整批失败
        for obj in batch:
            obj_id = obj.get("id", "unknown")
            failed_ids.append(obj_id)
            if failed_fh:
                failed_fh.write(json.dumps(
                    {"id": obj_id, "reason": str(e)[:200]},
                    ensure_ascii=False,
                ) + "\n")
        return {"accepted": 0}


if __name__ == "__main__":
    main()
