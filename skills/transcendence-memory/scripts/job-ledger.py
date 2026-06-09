#!/usr/bin/env python3
"""transcendence-memory async job ledger.

Tracks background knowledge-graph build jobs created by POST /documents/text
and POST /documents/upload (server v0.15.0+ enqueues these and returns a job
id immediately). Lets the agent stay fully non-blocking while still surfacing
build failures — silently on success, only loud on failure.

Subcommands:
  add    Read a server response JSON from stdin and append a ledger entry if
         it carries a job id (`pid` / `job_id`). No job id -> old synchronous
         server: exits 0 without writing the ledger (backward compatible).
  sweep  Poll every pending job once. done -> drop + quiet log; failed -> move
         to the failed ledger + print one warning line; running / unreachable
         -> keep. Always exits 0, never raises.
  list   Print pending / failed / recently-done jobs with live status. Backs
         the `/tm jobs` command.

Ledger files (under --config-dir, default ~/.transcendence-memory):
  pending-jobs.jsonl   active jobs        {job_id,container,endpoint,kind,source,submitted_at}
  failed-jobs.jsonl    jobs that failed   (entry + failed_at,exit_code,message)
  jobs.log             quiet append-only log of completed jobs

Test seam: --mock-jobs-dir DIR makes `sweep` / `list` read job status from
DIR/<job_id>.json instead of issuing HTTP requests.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".transcendence-memory")
# 非默认 User-Agent：Cloudflare WAF 会 1010 拦截 urllib 默认 UA
USER_AGENT = "transcendence-memory-skill/0.5"
HTTP_TIMEOUT = 8
SWEEP_CAP = 30  # 单次 sweep 最多探测的 job 数，其余留待下次会话
STATUS_RE = re.compile(r"status=([a-zA-Z]+)")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _paths(config_dir: str) -> dict:
    return {
        "pending": os.path.join(config_dir, "pending-jobs.jsonl"),
        "failed": os.path.join(config_dir, "failed-jobs.jsonl"),
        "log": os.path.join(config_dir, "jobs.log"),
        "config": os.path.join(config_dir, "config.toml"),
    }


def load_config(config_dir: str):
    """Return (endpoint, api_key) by scanning config.toml; ('', '') on miss."""
    endpoint = api_key = ""
    try:
        with open(_paths(config_dir)["config"], encoding="utf-8") as fh:
            for line in fh:
                s = line.strip()
                if s.startswith("endpoint") and "=" in s:
                    endpoint = s.split("=", 1)[1].strip().strip('"')
                elif s.startswith("api_key") and "=" in s:
                    api_key = s.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return endpoint, api_key


def read_jsonl(path: str) -> list:
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue  # 跳过损坏行，保持健壮
    except OSError:
        pass
    return out


def write_jsonl(path: str, entries: list) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def append_line(path: str, text: str) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(text + "\n")


def extract_job_id(resp: dict):
    """Return an int job id from a server response, or None for sync servers."""
    for key in ("pid", "job_id"):  # 客户端两者都接受，优先 pid
        val = resp.get(key)
        if isinstance(val, bool):
            continue
        if isinstance(val, int):
            return val
        if isinstance(val, str) and val.isdigit():
            return int(val)
    return None


def fetch_job(endpoint: str, api_key: str, job_id, mock_dir=None):
    """Return a job-status dict, or None on any failure (network / parse)."""
    if mock_dir:
        try:
            with open(os.path.join(mock_dir, f"{job_id}.json"), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None
    url = f"{endpoint.rstrip('/')}/jobs/{job_id}"
    req = urllib.request.Request(
        url, headers={"X-API-KEY": api_key, "User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None  # 不可达 / 超时 / 非 JSON —— 一律静默


def classify(job: dict) -> str:
    """Map a job-status dict to: running | done | failed | cancelled."""
    running = job.get("running")
    exit_code = job.get("exit_code")
    msg = job.get("message") or ""
    m = STATUS_RE.search(msg)
    status = m.group(1).lower() if m else ""
    if isinstance(exit_code, int) and not isinstance(exit_code, bool) and exit_code != 0:
        return "failed"
    if status in ("failed", "error"):
        return "failed"
    if status == "cancelled":
        return "cancelled"
    if status == "done":
        return "done"
    if running is True:
        return "running"
    if running is False and exit_code == 0:
        return "done"
    if status in ("pending", "running"):
        return "running"
    return "running"  # 信号不明确 —— 保留账本，留待下次确认


def cmd_add(args) -> int:
    raw = sys.stdin.read()
    try:
        resp = json.loads(raw)
    except ValueError:
        print("[transcendence-memory] 无法解析 server 响应，未记入后台账本。")
        return 0
    if not isinstance(resp, dict):
        print("[transcendence-memory] server 响应格式异常，未记入后台账本。")
        return 0
    job_id = extract_job_id(resp)
    if job_id is None:
        # 旧版 server（< v0.15.0）同步建图，响应无 job 标识 —— 优雅降级
        print("[transcendence-memory] server 已同步处理（旧版无异步队列），无需后台追踪。")
        return 0
    os.makedirs(args.config_dir, exist_ok=True)
    entry = {
        "job_id": job_id,
        "container": args.container,
        "endpoint": args.endpoint,
        "kind": args.kind,
        "source": args.source,
        "submitted_at": _now(),
    }
    append_line(_paths(args.config_dir)["pending"],
                json.dumps(entry, ensure_ascii=False))
    print(f"[transcendence-memory] 已入队后台建图（job {job_id}）；无需等待。"
          f"建好后下次会话自动可召回，失败会静默提示。可用 /tm jobs 查看。")
    return 0


def cmd_sweep(args) -> int:
    paths = _paths(args.config_dir)
    pending = read_jsonl(paths["pending"])
    if not pending:
        return 0  # 账本不存在 / 为空 —— 完全静默
    endpoint_cfg, api_key = load_config(args.config_dir)
    keep, warnings, checked = [], [], 0
    for entry in pending:
        job_id = entry.get("job_id")
        endpoint = entry.get("endpoint") or endpoint_cfg
        if job_id is None or checked >= SWEEP_CAP or not endpoint:
            keep.append(entry)
            continue
        checked += 1
        job = fetch_job(endpoint, api_key, job_id, args.mock_jobs_dir)
        if job is None:  # 网络失败 / server 不可达 → 静默保留，不报错
            keep.append(entry)
            continue
        verdict = classify(job)
        if verdict == "running":
            keep.append(entry)
        elif verdict in ("done", "cancelled"):
            append_line(paths["log"],
                        f"{_now()} {verdict} job={job_id} "
                        f"container={entry.get('container', '')} "
                        f"kind={entry.get('kind', '')} "
                        f"source={entry.get('source', '')}")
        else:  # failed —— 唯一会向用户显示的情况
            message = job.get("message") or "未知原因"
            rec = dict(entry)
            rec["failed_at"] = _now()
            rec["exit_code"] = job.get("exit_code")
            rec["message"] = message
            append_line(paths["failed"], json.dumps(rec, ensure_ascii=False))
            warnings.append(
                f"⚠️ 记忆建图 job {job_id} 失败：{message}，可用 /tm jobs 查看/重试")
    write_jsonl(paths["pending"], keep)
    for w in warnings:
        print(w)
    return 0


def cmd_list(args) -> int:
    paths = _paths(args.config_dir)
    pending = read_jsonl(paths["pending"])
    failed = read_jsonl(paths["failed"])
    endpoint_cfg, api_key = load_config(args.config_dir)

    print("=== transcendence-memory 后台建图 job ===\n")

    if pending:
        print(f"⏳ 进行中 / 待确认（{len(pending)}）：")
        for e in pending:
            job_id = e.get("job_id")
            endpoint = e.get("endpoint") or endpoint_cfg
            job = (fetch_job(endpoint, api_key, job_id, args.mock_jobs_dir)
                   if endpoint else None)
            live = classify(job) if job else "unreachable"
            print(f"  • job {job_id}  [{live}]  {e.get('kind', '')}  "
                  f"container={e.get('container', '')}  "
                  f"source={e.get('source', '')}  "
                  f"submitted={e.get('submitted_at', '')}")
    else:
        print("⏳ 进行中：无")

    if failed:
        print(f"\n❌ 失败（{len(failed)}，最近 10 条）：")
        for e in failed[-10:]:
            print(f"  • job {e.get('job_id')}  "
                  f"container={e.get('container', '')}  "
                  f"{e.get('failed_at', '')}  {e.get('message', '')}")
        print("\n  重试：用 /tm upload 重新上传文件，"
              "或在 /tm query 前重新 /documents/text 入库。")
    else:
        print("\n❌ 失败：无")

    done_tail = []
    try:
        with open(paths["log"], encoding="utf-8") as fh:
            done_tail = [ln.rstrip() for ln in fh if ln.strip()][-5:]
    except OSError:
        pass
    if done_tail:
        print("\n✅ 最近完成：")
        for ln in done_tail:
            print(f"  • {ln}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="transcendence-memory async job ledger")
    p.add_argument("--config-dir", default=DEFAULT_CONFIG_DIR,
                   help="ledger / config directory (default ~/.transcendence-memory)")
    p.add_argument("--mock-jobs-dir", default=None,
                   help="测试用：从 DIR/<job_id>.json 读 job 状态，不发 HTTP")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("add", help="从 stdin 读 server 响应并记入后台账本")
    pa.add_argument("--endpoint", default="")
    pa.add_argument("--container", default="")
    pa.add_argument("--kind", default="text", choices=["text", "upload"])
    pa.add_argument("--source", default="")

    sub.add_parser("sweep", help="静默轮询所有 pending job 一次")
    sub.add_parser("list", help="列出 pending / failed / 最近完成 job")

    args = p.parse_args(argv)
    try:
        if args.cmd == "add":
            return cmd_add(args)
        if args.cmd == "sweep":
            return cmd_sweep(args)
        if args.cmd == "list":
            return cmd_list(args)
    except Exception:
        # 永不让 hook / 命令因账本异常而失败或阻塞会话
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
