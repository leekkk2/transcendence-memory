#!/usr/bin/env python3
"""Bounded HTTP-only graph ingestion with a recoverable, endpoint-scoped ledger."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from redact import redact_text

logger = logging.getLogger('tm-graphify')
CONFIG_FILE = Path(os.environ.get('TM_CONFIG', Path.home() / '.transcendence-memory/config.toml'))
LEDGER_FILE = Path(os.environ.get('TM_GRAPHIFY_LEDGER', Path.home() / '.transcendence-memory/graphify-ledger.json'))


def load_config():
    import tomllib
    with CONFIG_FILE.open('rb') as stream:
        cfg = tomllib.load(stream)
    endpoint = cfg.get('connection', {}).get('endpoint', '').rstrip('/')
    key = cfg.get('auth', {}).get('api_key', '')
    if not endpoint or not key:
        raise ValueError('connection endpoint and API key are required')
    return endpoint, key


def api_call(endpoint, api_key, path, method='GET', body=None):
    headers = {'X-API-KEY': api_key, 'User-Agent': 'transcendence-memory-graphify/2.0'}
    data = None
    if body is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(body).encode()
    request = urllib.request.Request(endpoint + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        logger.error('HTTP %s for %s', exc.code, path)
        raise


def get_aliases(endpoint, api_key):
    data = api_call(endpoint, api_key, '/containers/aliases')
    rows = data if isinstance(data, list) else data.get('aliases', [])
    return ({r['alias']: r['canonical'] for r in rows if r.get('status') in ('active', 'deprecated')},
            {r['alias'] for r in rows if r.get('status') == 'removed'})


def load_ledger(endpoint=''):
    if not LEDGER_FILE.exists():
        return {'schema': 2, 'endpoint': endpoint.rstrip('/'), 'containers': {}}
    data = json.loads(LEDGER_FILE.read_text())
    if data.get('schema') != 2 or not isinstance(data.get('containers'), dict):
        raise ValueError('ledger requires reviewed migration; refusing an empty restart')
    if endpoint and data.get('endpoint') != endpoint.rstrip('/'):
        raise ValueError('ledger endpoint mismatch')
    return data


def save_ledger(ledger):
    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER_FILE.with_name(LEDGER_FILE.name + '.' + str(os.getpid()) + '.tmp')
    ledger['updated_at'] = int(time.time())
    try:
        with tmp.open('w') as stream:
            os.chmod(tmp, 0o600)
            json.dump(ledger, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, LEDGER_FILE)
        if os.name == 'posix':
            fd = os.open(LEDGER_FILE.parent, os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
    finally:
        tmp.unlink(missing_ok=True)


@contextmanager
def ledger_lock():
    # Atomic mkdir works on all supported clients; stale locks require review.
    lock = LEDGER_FILE.with_name(LEDGER_FILE.name + '.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    try: lock.mkdir()
    except FileExistsError: raise RuntimeError('ledger is locked; inspect its owner before recovery')
    try:
        (lock / 'owner.json').write_text(json.dumps({'pid': os.getpid(), 'created': time.time()}))
        yield
    finally:
        (lock / 'owner.json').unlink(missing_ok=True)
        lock.rmdir()


def memory_fingerprint(item):
    fields = {k: item.get(k) for k in ('id', 'title', 'text', 'tags', 'updatedAt')}
    return hashlib.sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def get_container_memories(container_name, input_file=None, *, endpoint=None, api_key=None):
    if input_file:
        with Path(input_file).open() as stream:
            return [json.loads(line) for line in stream if line.strip()]
    if not endpoint:
        raise ValueError('HTTP endpoint required; database/Docker discovery is disabled')
    items, seen, total = [], set(), None
    while total is None or len(items) < total:
        path = '/containers/' + urllib.parse.quote(container_name, safe='') + '/memories'
        result = api_call(endpoint, api_key, path + f'?limit=500&offset={len(items)}')
        if total is not None and result['total'] != total:
            raise RuntimeError('source changed during pagination; retry a stable snapshot')
        total = result['total']
        page = result.get('items', [])
        if not page and len(items) < total:
            raise RuntimeError('incomplete source pagination')
        for item in page:
            identity = item.get('id') or memory_fingerprint(item)
            if identity in seen:
                raise RuntimeError('duplicate source identity; pagination snapshot changed')
            seen.add(identity)
        items.extend(page)
    return items


def cluster_memories(items, max_chars_per_doc=3500, redact=True):
    if not redact:
        raise ValueError('credential redaction cannot be disabled')
    if max_chars_per_doc < 512:
        raise ValueError('document character limit must be at least 512')
    cards = []
    for item in sorted(items, key=lambda x: str(x.get('id') or memory_fingerprint(x))):
        text = item.get('text') or ''
        if not text.strip() or set(item.get('tags') or []) & {'pre-delete-backup', '删除'}:
            continue
        fingerprint = memory_fingerprint(item)
        title = redact_text(str(item.get('title') or 'Memory'))[:160]
        header = f'# {title}\nSource version: {fingerprint}\n\n'
        body = redact_text(text)
        step = max_chars_per_doc - len(header) - 40
        for offset in range(0, len(body), step):
            piece = body[offset:offset + step]
            content = header + f'Part: {offset // step + 1}\n\n' + piece
            cards.append({'title': title, 'text': content, 'source_text': piece,
                          'mem_ids': [item.get('id')], 'fingerprint': fingerprint,
                          'content_hash': hashlib.sha256(content.encode()).hexdigest()})
    return cards


def target_containers(rows, aliases, removed):
    targets = set()
    for row in rows:
        name = row.get('name') or row.get('container')
        if not name or name.startswith('__') or name in removed:
            continue
        canonical = aliases.get(name, name)
        if canonical not in removed:
            targets.add(canonical)
    return sorted(targets)


def status(endpoint, key, aliases, removed, ledger):
    rows = api_call(endpoint, key, '/containers').get('containers', [])
    failures = 0
    for name in target_containers(rows, aliases, removed):
        try:
            graph = api_call(endpoint, key, '/admin/containers/' + urllib.parse.quote(name, safe='') + '/graph')
            memories = api_call(endpoint, key, '/containers/' + urllib.parse.quote(name, safe='') + '/memories?limit=1&offset=0')
            entries = ledger['containers'].get(name, {}).get('cards', {})
            done = sum(v.get('state') == 'done' for v in entries.values())
            print(json.dumps({'container': name, 'objects': memories['total'],
                              'nodes': graph.get('node_count'), 'edges': graph.get('edge_count'),
                              'ledger_done_cards': done, 'coverage': 'unknown'}, ensure_ascii=False))
        except Exception as exc:
            failures += 1
            logger.error('status failed for %s: %s', name, type(exc).__name__)
    return int(bool(failures))


def wait_for_job(endpoint, key, pid, max_wait_sec=600):
    deadline = time.monotonic() + max_wait_sec
    while time.monotonic() < deadline:
        result = api_call(endpoint, key, f'/jobs/{pid}')
        if not result.get('running', True):
            if result.get('exit_code') != 0:
                raise RuntimeError('graph job failed; inspect server job before retry')
            return
        time.sleep(5)
    raise RuntimeError('job still pending; retained for the next resume')


def process_container(endpoint, key, ledger, name, *, dry_run, input_file, budget, max_chars, wait_seconds):
    memories = get_container_memories(name, input_file, endpoint=endpoint, api_key=key)
    cards = cluster_memories(memories)
    entry = ledger['containers'].setdefault(name, {'cards': {}})
    records = entry['cards']
    if not dry_run and not records:
        graph = api_call(endpoint, key, '/admin/containers/' + urllib.parse.quote(name, safe='') + '/graph')
        if graph.get('node_count', 0) or graph.get('edge_count', 0):
            raise RuntimeError('existing graph has no ledger baseline; reconcile sources before applying')
    used_chars = 0
    for card in cards:
        digest = card['content_hash']
        record = records.get(digest, {})
        if record.get('state') == 'done': continue
        if record.get('state') == 'submitting':
            raise RuntimeError('uncertain submission; reconcile server jobs before resuming')
        if budget[0] <= 0 or used_chars + len(card['text']) > max_chars: break
        if dry_run:
            print(json.dumps({'container': name, 'hash': digest, 'chars': len(card['text'])}))
        else:
            if not record.get('pid'):
                records[digest] = {'state': 'submitting', 'fingerprint': card['fingerprint']}
                save_ledger(ledger)
                result = api_call(endpoint, key, '/documents/text', method='POST', body={
                    'container': name, 'text': card['text'], 'description': 'graphify:' + digest,
                })
                if not result.get('pid'): raise RuntimeError('server did not return a job identifier')
                records[digest].update(state='pending', pid=result['pid'])
                save_ledger(ledger)
            wait_for_job(endpoint, key, records[digest]['pid'], wait_seconds)
            records[digest].update(state='done', completed_at=int(time.time()))
            save_ledger(ledger)
        budget[0] -= 1
        used_chars += len(card['text'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--container', '-c')
    parser.add_argument('--input', '-i')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--max-documents', type=int, default=20)
    parser.add_argument('--max-chars', type=int, default=50000)
    parser.add_argument('--wait-seconds', type=int, default=600)
    args = parser.parse_args()
    if args.all and args.input: parser.error('--input requires one explicit container')
    if args.all and args.container: parser.error('choose --all or --container')
    if min(args.max_documents, args.max_chars, args.wait_seconds) <= 0: parser.error('budgets must be positive')
    endpoint, key = load_config()
    aliases, removed = get_aliases(endpoint, key)
    if args.status: return status(endpoint, key, aliases, removed, load_ledger(endpoint))
    if not args.all and not args.container: parser.error('--container, --all or --status required')
    if args.container in removed: raise ValueError('container was removed')
    with ledger_lock():
        ledger = load_ledger(endpoint)
        names = target_containers(api_call(endpoint, key, '/containers')['containers'], aliases, removed) if args.all else [aliases.get(args.container, args.container)]
        budget = [args.max_documents]
        for name in names:
            process_container(endpoint, key, ledger, name, dry_run=args.dry_run,
                              input_file=args.input, budget=budget, max_chars=args.max_chars,
                              wait_seconds=args.wait_seconds)
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    try: sys.exit(main())
    except Exception as exc:
        logger.error('%s', redact_text(str(exc)))
        sys.exit(1)
