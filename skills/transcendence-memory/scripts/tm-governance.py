#!/usr/bin/env python3
"""Config-driven governance client. Dry-run by default; no automatic write retries."""
import argparse
import json
import os
from pathlib import Path
import sys
import tomllib
import urllib.error
import urllib.request

TOOLS={'compress_knowledge_cluster','update_container_routing','snapshot_and_quarantine',
       'tune_model_parameters','analyze_retrieval_latency','manage_token_quotas'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['tools','invoke'])
    parser.add_argument('tool',nargs='?',choices=sorted(TOOLS))
    parser.add_argument('--container')
    parser.add_argument('--params-file',type=Path)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--confirm-quarantine',action='store_true')
    args=parser.parse_args()
    if args.command=='invoke' and not args.tool: parser.error('invoke requires a tool')
    if args.apply and args.tool=='snapshot_and_quarantine' and not args.confirm_quarantine:
        parser.error('Review the dry-run plan; explicit --confirm-quarantine is required for apply')
    cfg=tomllib.loads(Path(os.environ.get('TM_CONFIG_FILE',str(Path.home()/'.transcendence-memory/config.toml'))).read_text())
    connection=cfg.get('connection',cfg);auth=cfg.get('auth',cfg)
    headers={'X-API-KEY':auth['api_key'],'User-Agent':'transcendence-memory-skill/0.6','Content-Type':'application/json'}
    path='/admin/tools';body=None
    if args.command=='invoke':
        params=json.loads(args.params_file.read_text()) if args.params_file else {}
        if not isinstance(params,dict):parser.error('params-file must contain a JSON object')
        if args.tool=='update_container_routing' and not isinstance(params.get('rules'),dict):
            parser.error('routing requires a params-file containing {"rules": {...}}')
        container=args.container or connection.get('container')
        if not container and args.tool!='manage_token_quotas':parser.error('container is required')
        body={'container':container,'params':params,'dry_run':not args.apply}
        path=f'/admin/tools/{args.tool}/invoke'
    request=urllib.request.Request(connection['endpoint'].rstrip('/')+path,
        data=json.dumps(body).encode() if body else None,headers=headers)
    try:
        with urllib.request.urlopen(request,timeout=300 if args.apply else 60) as response:
            result=json.load(response)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 1 if result.get('status') in ('error','disabled','deferred') else 0
    except urllib.error.HTTPError as exc:
        print(f'HTTP {exc.code}; request={exc.headers.get("X-Request-ID", "unknown")}',file=sys.stderr)
        print(exc.read().decode(),file=sys.stderr)
        return 1
    except (OSError,ValueError) as exc:
        print(f'{type(exc).__name__}: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
