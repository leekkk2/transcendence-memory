#!/usr/bin/env python3
"""Install a complete skill plus the existing native Python CLI, without global rules edits."""
import argparse,json,os,pathlib,shutil,subprocess,sys,time,venv,hashlib


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()


def install(args):
    root=pathlib.Path(__file__).resolve().parents[1]
    remote=git(root,'remote','get-url','origin').removesuffix('.git')
    if remote not in ['https://github.com/leekkk2/transcendence-memory','git@github.com:leekkk2/transcendence-memory']:
        raise RuntimeError('Unexpected repository origin; verify the checkout before installation')
    if git(root,'status','--porcelain') and not args.allow_dirty:
        raise RuntimeError('Checkout has local changes; use --allow-dirty only for development')
    if args.update:
        if git(root,'status','--porcelain'):raise RuntimeError('Checkout has local changes; update refused')
        git(root,'pull','--ff-only')
    home=pathlib.Path(args.home).expanduser().resolve()
    state=home/'.transcendence-memory';state.mkdir(parents=True,exist_ok=True)
    if os.name!='nt':state.chmod(0o700)
    target=home/'.agents/skills/transcendence-memory'
    if target.resolve()==root or root in target.resolve().parents:
        raise RuntimeError('Checkout occupies the skill destination. Keep checkout separately and rerun; no files changed.')
    source=root/'skills/transcendence-memory'
    for item in ['SKILL.md','references/api-reference.md','scripts/tm-search.sh','scripts/redact.py']:
        if not (source/item).is_file():raise RuntimeError('Incomplete skill checkout: '+item)
    manifest=state/'install.json'
    args.agents=args.agents or (json.loads(manifest.read_text())['agents'] if manifest.exists() else ['codex','gemini'])
    if target.exists() and not manifest.exists() and not args.replace_existing:
        raise RuntimeError('Existing unmanaged skill; use --replace-existing after review (a backup will be retained)')
    # Verify all entry conflicts before replacing a working installation.
    for name,agent_dir in [('codex','.codex'),('gemini','.gemini'),('claude','.claude')]:
        if name in args.agents:
            link=home/agent_dir/'skills/transcendence-memory'
            if (link.exists() or link.is_symlink()) and link.resolve()!=target.resolve():
                raise RuntimeError(f'Existing agent entry differs: {link}; preserved')
    previous = json.loads(manifest.read_text()) if manifest.exists() else None
    if previous and not args.replace_existing:
        for name,digest in previous.get('files',{}).items():
            file=target/name
            if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=digest:
                raise RuntimeError('Installed skill has local edits; preserved: '+name)
    if not args.skip_cli:
        env=state/'runtimes'/str(time.time_ns());venv.EnvBuilder(with_pip=True).create(env)
        python=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        ref=args.cli_source or json.loads((root/'cli-source.json').read_text())['requirement']
        subprocess.run([str(python),'-m','pip','install',ref],check=True)
        subprocess.run([str(python),'-c','import tm_cli.main'],check=True)
    else:python=pathlib.Path(sys.executable)
    stage=target.with_name('.transcendence-memory.stage-'+str(time.time_ns()))
    stage.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(source,stage)
    backup=None
    if target.exists() or target.is_symlink():
        backup=state/'backups'/str(time.time_ns());backup.parent.mkdir(parents=True,exist_ok=True);target.rename(backup)
    created=[]
    try:
        stage.rename(target)
        for name,agent_dir in [('codex','.codex'),('gemini','.gemini'),('claude','.claude')]:
            if name not in args.agents:continue
            link=home/agent_dir/'skills/transcendence-memory';link.parent.mkdir(parents=True,exist_ok=True)
            if link.exists() or link.is_symlink():
                if link.resolve()==target.resolve():continue
                raise RuntimeError(f'Existing agent entry differs: {link}; preserved, resolve explicitly')
            if os.name=='nt':
                # PowerShell creates a directory junction with no developer-mode requirement.
                envvars=os.environ.copy();envvars.update(TM_LINK=str(link),TM_TARGET=str(target))
                subprocess.run(['powershell','-NoProfile','-Command','New-Item -ItemType Junction -Path $env:TM_LINK -Target $env:TM_TARGET | Out-Null'],check=True,env=envvars)
            else:link.symlink_to(target,target_is_directory=True)
            created.append(link)
        result={'schema':1,'repo_root':str(root),'skill_root':str(target),'source_revision':git(root,'rev-parse','HEAD'),
                'python_executable':str(python),'backup':str(backup) if backup else None,'agents':args.agents,'previous':previous,'files':{str(f.relative_to(target)):hashlib.sha256(f.read_bytes()).hexdigest() for f in target.rglob('*') if f.is_file() and '__pycache__' not in f.parts}}
        temporary=manifest.with_suffix('.tmp')
        temporary.write_text(json.dumps(result,indent=2)+'\n')
        if os.name!='nt':temporary.chmod(0o600)
        temporary.replace(manifest)
        print(json.dumps(result,indent=2))
    except Exception:
        for link in reversed(created):
            if os.name=='nt':os.rmdir(link)
            else:link.unlink()
        if target.exists():shutil.rmtree(target)
        if backup:backup.rename(target)
        raise




def rollback(args):
    home=pathlib.Path(args.home).expanduser().resolve();state=home/'.transcendence-memory'
    manifest=state/'install.json'
    current=json.loads(manifest.read_text());target=pathlib.Path(current['skill_root'])
    if target != home/'.agents/skills/transcendence-memory':raise RuntimeError('Manifest target mismatch')
    for name,digest in current['files'].items():
        file=target/name
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Installed skill has local edits; rollback preserved it: '+name)
    backup=pathlib.Path(current['backup']) if current.get('backup') else None
    if backup and (not backup.is_dir() or backup.parent!=state/'backups'):
        raise RuntimeError('Backup missing or outside state directory')
    retired=state/'backups'/('removed-'+str(time.time_ns()));retired.parent.mkdir(parents=True,exist_ok=True)
    target.rename(retired)
    if backup:backup.rename(target)
    previous=current.get('previous')
    for name,agent_dir in [('codex','.codex'),('gemini','.gemini'),('claude','.claude')]:
        if name not in current['agents'] or (previous and name in previous['agents']):continue
        link=home/agent_dir/'skills/transcendence-memory'
        if link.resolve()!=target.resolve():continue
        if os.name=='nt':os.rmdir(link)
        else:link.unlink()
    if previous:
        temp=manifest.with_suffix('.tmp');temp.write_text(json.dumps(previous,indent=2)+'\n')
        if os.name!='nt':temp.chmod(0o600)
        temp.replace(manifest)
    else:manifest.rename(state/('uninstalled-'+str(time.time_ns())+'.json'))
    print(json.dumps({'restored_previous':bool(previous),'retained_removed_skill':str(retired)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',default=str(pathlib.Path.home()))
    p.add_argument('--agents',nargs='+',choices=['codex','gemini','claude'],default=None)
    p.add_argument('--cli-source');p.add_argument('--skip-cli',action='store_true');p.add_argument('--update',action='store_true');p.add_argument('--replace-existing',action='store_true');p.add_argument('--allow-dirty',action='store_true')
    p.add_argument('--rollback',action='store_true',help='Restore previous install or remove first managed install; preserve backups and config')
    args=p.parse_args()
    rollback(args) if args.rollback else install(args)
