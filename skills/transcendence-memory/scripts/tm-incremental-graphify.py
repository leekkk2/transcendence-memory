#!/usr/bin/env python3
"""Incremental Knowledge Graph Builder for Transcendence Memory Server.

Converts LanceDB memory_objects into LightRAG Knowledge Graph documents,
grouped by topic/tags, maintaining an incremental ledger to prevent duplicates
and avoid memory spikes / OOM issues. Includes built-in secret redaction.

Usage:
  python3 tm-incremental-graphify.py [--container <name>] [--dry-run] [--status] [--all]
"""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("tm-graphify")

CONFIG_FILE = Path(os.environ.get("TM_CONFIG", Path.home() / ".transcendence-memory/config.toml"))
LEDGER_FILE = Path(os.environ.get("TM_GRAPHIFY_LEDGER", Path.home() / ".transcendence-memory/graphify-ledger.json"))

# Attempt import of standard secret redaction module
try:
    from redact import redact_text
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from redact import redact_text
    except ImportError:
        def redact_text(val: str) -> str:
            return val


def load_config():
    if not CONFIG_FILE.is_file():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE}")
    import tomllib
    with open(CONFIG_FILE, "rb") as f:
        cfg = tomllib.load(f)
    endpoint = cfg.get("connection", {}).get("endpoint", "http://127.0.0.1:8711").rstrip("/")
    api_key = cfg.get("auth", {}).get("api_key", "")
    return endpoint, api_key


def api_call(endpoint, api_key, path, method="GET", body=None):
    url = f"{endpoint}{path}"
    headers = {
        "X-API-KEY": api_key,
        "User-Agent": "transcendence-memory-graphify/1.0",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        logger.error(f"HTTP {e.code} for {path}: {err_body}")
        raise


def get_aliases(endpoint, api_key):
    try:
        data = api_call(endpoint, api_key, "/containers/aliases")
        rows = data if isinstance(data, list) else data.get("aliases", [])
        mapping = {}
        for row in rows:
            if row.get("status") in ("active", "deprecated"):
                mapping[row["alias"]] = row["canonical"]
        return mapping
    except Exception as e:
        logger.warning(f"Could not load aliases: {e}")
        return {}


def load_ledger() -> dict:
    if LEDGER_FILE.is_file():
        try:
            with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read ledger: {e}, starting fresh.")
    return {"containers": {}, "updated_at": 0}


def save_ledger(ledger: dict):
    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = int(time.time())
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)


def wait_for_job(endpoint, api_key, pid: int, max_wait_sec: int = 600) -> bool:
    start_time = time.time()
    logger.info(f"Waiting for KG build job {pid} to complete...")
    while time.time() - start_time < max_wait_sec:
        try:
            res = api_call(endpoint, api_key, f"/jobs/{pid}")
            running = res.get("running", True)
            exit_code = res.get("exit_code")
            if not running:
                if exit_code == 0:
                    logger.info(f"Job {pid} completed successfully.")
                    return True
                else:
                    logger.error(f"Job {pid} failed with exit_code={exit_code}: {res.get('message')}")
                    return False
        except Exception as e:
            logger.warning(f"Error checking job {pid}: {e}")
        time.sleep(5)
    logger.error(f"Job {pid} timed out after {max_wait_sec}s.")
    return False


def _find_docker_container(explicit: str | None = None) -> str | None:
    if explicit:
        return explicit
    env_c = os.environ.get("TM_DOCKER_CONTAINER")
    if env_c:
        return env_c
    try:
        res = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=False
        )
        for name in res.stdout.splitlines():
            name = name.strip()
            if "rag-server" in name or "transcendence-memory" in name:
                return name
    except Exception:
        pass
    return None


def get_container_memories(container_name: str, input_file: str | None = None, docker_container: str | None = None) -> list[dict]:
    # 1. Direct input file takes highest precedence
    if input_file and os.path.isfile(input_file):
        with open(input_file, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    # 2. Local filesystem check (if running on same host / volume mounted)
    ws_env = os.environ.get("WORKSPACE", "/data")
    local_path = Path(ws_env) / "tasks" / "rag" / "containers" / container_name / "memory_objects.jsonl"
    if local_path.is_file():
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return [json.loads(line) for line in f if line.strip()]
        except Exception as e:
            logger.warning(f"Could not read local {local_path}: {e}")

    # 3. Docker exec inspection
    target_docker = _find_docker_container(docker_container)
    if target_docker:
        cmd = [
            "docker", "exec", target_docker,
            "python3", "-c",
            f"""
import json, os
path = '/data/tasks/rag/containers/{container_name}/memory_objects.jsonl'
if not os.path.isfile(path):
    print(json.dumps([]))
else:
    with open(path, 'r', encoding='utf-8') as f:
        rows = [json.loads(l) for l in f if l.strip()]
    print(json.dumps(rows))
"""
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(res.stdout)
        except Exception as e:
            logger.error(f"Docker read failed on {target_docker}: {e}")

    logger.warning(f"No memory objects found for container '{container_name}'. Use --input to specify JSONL.")
    return []


def cluster_memories(items: list[dict], max_chars_per_doc: int = 3500, redact: bool = True) -> list[dict]:
    """Group memories into cohesive markdown knowledge documents."""
    docs = []
    
    # 1. Filter out ephemeral / dump / pre-delete items
    filtered = []
    for item in items:
        tags = set(item.get("tags") or [])
        text = item.get("text", "").strip()
        if not text:
            continue
        # Skip pure low-value dumps
        if "pre-delete-backup" in tags or "删除" in tags:
            continue
        filtered.append(item)

    if not filtered:
        return []

    # 2. Cluster by Primary Topic / Tag
    clusters = defaultdict(list)
    for item in filtered:
        tags = item.get("tags") or []
        # Find the most distinctive tag
        key_tag = "general"
        for t in tags:
            t_lower = t.lower()
            if any(k in t_lower for k in ["sop", "decision", "architecture", "migration", "concurrency", "ota", "asc", "playbook"]):
                key_tag = t
                break
            elif ":" in t:
                k, v = t.split(":", 1)
                if k in ("topic", "category", "project"):
                    key_tag = v
                    break
        clusters[key_tag].append(item)

    # 3. Format each cluster into Markdown
    for topic, cluster_items in clusters.items():
        # Split into chunks if too long
        current_batch = []
        current_len = 0
        batch_idx = 1

        for it in cluster_items:
            it_len = len(it.get("text", ""))
            if current_len + it_len > max_chars_per_doc and current_batch:
                docs.append(_format_markdown_card(topic, current_batch, batch_idx, redact=redact))
                batch_idx += 1
                current_batch = [it]
                current_len = it_len
            else:
                current_batch.append(it)
                current_len += it_len

        if current_batch:
            docs.append(_format_markdown_card(topic, current_batch, batch_idx, redact=redact))

    return docs


def _format_markdown_card(topic: str, items: list[dict], batch_idx: int, redact: bool = True) -> dict:
    mem_ids = [it.get("id") for it in items if it.get("id")]
    all_tags = set()
    for it in items:
        all_tags.update(it.get("tags") or [])
    
    title = f"# 【知识图谱聚合卡片】主题：{topic.upper()} (第{batch_idx}组)"
    meta = f"> 本文档自动聚合并增量提炼自 {len(items)} 条结构化记忆对象，涵盖核心决策、架构规范、避坑指南与实战 SOP。\n\n"
    meta += f"- **记忆条目**: {', '.join(str(i) for i in mem_ids)}\n"
    meta += f"- **语义标签**: {', '.join(sorted(all_tags))}\n\n---\n\n"
    
    body = ""
    for it in items:
        it_id = it.get("id", "unknown")
        it_title = it.get("title") or it_id
        it_text = it.get("text", "").strip()
        body += f"## 条目：{it_title}\n"
        body += f"**ID**: `{it_id}` | **标签**: {', '.join(it.get('tags') or [])}\n\n"
        body += f"{it_text}\n\n---\n\n"

    full_text = title + "\n\n" + meta + body
    if redact:
        full_text = redact_text(full_text)

    content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
    
    return {
        "title": f"{topic} (第{batch_idx}组)",
        "mem_ids": mem_ids,
        "text": full_text,
        "content_hash": content_hash,
    }


def process_container(endpoint, api_key, aliases: dict, ledger: dict, container_name: str,
                      dry_run: bool = False, input_file: str | None = None,
                      docker_container: str | None = None, redact: bool = True):
    canonical_name = aliases.get(container_name, container_name)
    logger.info(f"Processing container: '{container_name}' (canonical: '{canonical_name}')")

    # Load memories
    memories = get_container_memories(container_name, input_file=input_file, docker_container=docker_container)
    logger.info(f"Loaded {len(memories)} memories for '{container_name}'.")

    # Check ledger for already processed IDs
    cont_ledger = ledger["containers"].setdefault(canonical_name, {
        "processed_ids": [],
        "documents_count": 0,
        "last_run": 0
    })
    processed_set = set(cont_ledger.get("processed_ids", []))

    unprocessed = [m for m in memories if m.get("id") not in processed_set]
    logger.info(f"Unprocessed memories: {len(unprocessed)} / {len(memories)}")

    if not unprocessed:
        logger.info(f"No new memories to graphify for '{container_name}'.")
        return

    # Cluster into markdown documents
    doc_cards = cluster_memories(unprocessed, redact=redact)
    logger.info(f"Synthesized into {len(doc_cards)} knowledge graph cards.")

    if dry_run:
        for idx, card in enumerate(doc_cards, 1):
            logger.info(f"[DRY-RUN] Card {idx}: {card['title']} ({len(card['mem_ids'])} items, {len(card['text'])} chars)")
        return

    for idx, card in enumerate(doc_cards, 1):
        logger.info(f"Ingesting Card {idx}/{len(doc_cards)}: '{card['title']}' ({len(card['text'])} chars)...")
        payload = {
            "container": canonical_name,
            "text": card["text"],
            "description": f"KG-Card: {card['title']}"
        }
        res = api_call(endpoint, api_key, "/documents/text", method="POST", body=payload)
        pid = res.get("pid")
        if not pid:
            logger.error(f"Failed to enqueue card: {res}")
            continue

        # Wait for worker to finish before next card to prevent memory buildup
        ok = wait_for_job(endpoint, api_key, pid)
        if ok:
            cont_ledger["processed_ids"].extend(card["mem_ids"])
            cont_ledger["documents_count"] = cont_ledger.get("documents_count", 0) + 1
            cont_ledger["last_run"] = int(time.time())
            save_ledger(ledger)
            logger.info(f"Card {idx} successfully indexed and ledger updated.")
        else:
            logger.error(f"Failed to process card {idx}, halting container ingestion to protect system.")
            break


def main():
    parser = argparse.ArgumentParser(description="Transcendence Memory Incremental Graph Builder")
    parser.add_argument("--container", "-c", help="Target container (e.g. my-container)")
    parser.add_argument("--input", "-i", help="Direct JSONL file containing memory objects")
    parser.add_argument("--docker-container", help="Docker container name to query memories from (auto-detected if omitted)")
    parser.add_argument("--no-redact", action="store_true", help="Disable automatic credential redaction")
    parser.add_argument("--all", action="store_true", help="Process all registered active containers")
    parser.add_argument("--dry-run", action="store_true", help="Preview clustering without submitting jobs")
    parser.add_argument("--status", action="store_true", help="Show current graph and ledger status across containers")
    args = parser.parse_args()

    endpoint, api_key = load_config()
    aliases = get_aliases(endpoint, api_key)
    ledger = load_ledger()
    redact = not args.no_redact

    if args.status:
        logger.info(f"Transcendence Memory Status for {endpoint}:")
        containers_res = api_call(endpoint, api_key, "/containers")
        for row in containers_res.get("containers", []):
            cname = row.get("name") or row.get("container")
            if not cname:
                continue
            canonical = aliases.get(cname, cname)
            # Query graph size
            try:
                graph_data = api_call(endpoint, api_key, f"/admin/containers/{cname}/graph")
            except Exception:
                graph_data = {"node_count": 0, "edge_count": 0}
            l_info = ledger.get("containers", {}).get(canonical, {})
            p_count = len(l_info.get("processed_ids", []))
            logger.info(
                f"Container '{cname}' -> canonical '{canonical}': "
                f"Objects: {row.get('objects') or row.get('object_count', 0)} | "
                f"Graph: {graph_data.get('node_count', 0)} nodes, {graph_data.get('edge_count', 0)} edges | "
                f"Ledger Processed: {p_count} IDs"
            )
        return

    if args.container:
        process_container(endpoint, api_key, aliases, ledger, args.container,
                          dry_run=args.dry_run, input_file=args.input,
                          docker_container=args.docker_container, redact=redact)
    elif args.all:
        containers_res = api_call(endpoint, api_key, "/containers")
        for row in containers_res.get("containers", []):
            cname = row.get("name") or row.get("container")
            if not cname or cname.startswith("__"):
                continue
            process_container(endpoint, api_key, aliases, ledger, cname,
                              dry_run=args.dry_run, input_file=args.input,
                              docker_container=args.docker_container, redact=redact)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
