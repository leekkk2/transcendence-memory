#!/usr/bin/env python3
"""Update existing Linux agent users with the managed installer; dry-run by default.
Run as root. Credentials/global agent rules remain in their original locations.
"""
import argparse,hashlib,json,os,pathlib,pwd,shutil,subprocess,sys,time
AGENTS={'codex':'.codex','gemini':'.gemini','claude':'.claude','cursor':'.cursor','opencode':'.config/opencode','antigravity':'.gemini/antigravity'}
ROOT=pathlib.Path(__file__).resolve().parents[1]
def candidates():
 return [u for u in pwd.getpwall() if (u.pw_uid==0 or 1000<=u.pw_uid<60000) and pathlib.Path(u.pw_dir).is_dir() and any((pathlib.Path(u.pw_dir)/d).is_dir() for d in AGENTS.values())]
def fingerprint(path):return hashlib.sha256(path.read_bytes()).digest() if path.exists() else None
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--cli-source',required=True);p.add_argument('--users',nargs='+');a=p.parse_args()
 if not sys.platform.startswith('linux') or os.geteuid()!=0:raise SystemExit('Run on Linux as root')
 users=candidates()
 if a.users:
  users=[u for u in users if u.pw_name in a.users]
  if set(a.users)!={u.pw_name for u in users}:raise SystemExit('A requested user has no discoverable agent home')
 plan=[{'user':u.pw_name,'home':u.pw_dir,'agents':[n for n,d in AGENTS.items() if (pathlib.Path(u.pw_dir)/d).exists()]} for u in users]
 if not a.apply:print(json.dumps({'dry_run':True,'users':plan},indent=2));return
 launcher=pathlib.Path('/usr/local/bin/tm')
 launcher_body='''#!/usr/bin/env python3
# Managed Transcendence Memory CLI launcher.
import json,os,pathlib,sys
p=pathlib.Path.home()/'.transcendence-memory/install.json'
if not p.is_file():raise SystemExit('No managed Transcendence Memory install for this user')
python=json.loads(p.read_text())['python_executable']
os.execv(python,[python,'-m','tm_cli.main',*sys.argv[1:]])
'''
 if launcher.exists() and 'Managed Transcendence Memory CLI launcher' not in launcher.read_text(errors='replace'):
  raise SystemExit('Existing /usr/local/bin/tm is not ours; preserved')
 results=[]
 for u,row in zip(users,plan):
  home=pathlib.Path(u.pw_dir);state=home/'.transcendence-memory';state.mkdir(mode=0o700,exist_ok=True);os.chown(state,u.pw_uid,u.pw_gid)
  backup=state/'backups'/('global-'+str(time.time_ns()));backup.mkdir(parents=True,mode=0o700);os.chown(backup.parent,u.pw_uid,u.pw_gid);os.chown(backup,u.pw_uid,u.pw_gid)
  target=home/'.agents/skills/transcendence-memory';moved=[]
  config=state/'config.toml';before=fingerprint(config)
  # Preserve independent copies so every discovery entry resolves to one managed tree.
  for agent in row['agents']:
   entry=home/AGENTS[agent]/'skills/transcendence-memory'
   if (entry.exists() or entry.is_symlink()) and entry.resolve()!=target.resolve():
    dest=backup/(agent+'-transcendence-memory');entry.rename(dest);moved.append((entry,dest))
  core=[n for n in row['agents'] if n in ('codex','gemini','claude')]
  command=['sudo','-H','-u',u.pw_name,'env','GIT_CONFIG_COUNT=1','GIT_CONFIG_KEY_0=safe.directory','GIT_CONFIG_VALUE_0='+str(ROOT),sys.executable,str(ROOT/'scripts/install.py'),'--home',str(home),'--replace-existing','--cli-source',a.cli_source,'--agents',*(core or ['codex'])]
  try:subprocess.run(command,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  except Exception:
   for entry,dest in moved:dest.rename(entry)
   raise RuntimeError('Managed install failed for '+u.pw_name+'; prior independent entries restored')
  alias=home/'.agents/skills/tm'
  if alias.exists() or alias.is_symlink():alias.rename(backup/'tm-alias')
  shutil.copytree(ROOT/'skills/tm',alias)
  for f in [alias,*alias.rglob('*')]:os.chown(f,u.pw_uid,u.pw_gid)
  for agent in row['agents']:
   directory=home/AGENTS[agent]/'skills';directory.mkdir(parents=True,exist_ok=True);os.chown(directory,u.pw_uid,u.pw_gid)
   for name,dest in [('transcendence-memory',target),('tm',alias)]:
    link=directory/name
    if link==dest:continue
    if link.exists() or link.is_symlink():
     if link.resolve()==dest.resolve():continue
     link.rename(backup/(agent+'-'+name))
    link.symlink_to(dest,target_is_directory=True);os.lchown(link,u.pw_uid,u.pw_gid)
  if before!=fingerprint(config):raise RuntimeError('Existing config unexpectedly changed')
  manifest=json.loads((state/'install.json').read_text());expected=manifest['files']
  assert all(hashlib.sha256((target/f).read_bytes()).hexdigest()==value for f,value in expected.items())
  result={**row,'revision':manifest['source_revision'],'config_unchanged':True,'files_verified':len(expected),'backup':str(backup)}
  (state/'global-install.json').write_text(json.dumps(result,indent=2)+'\n');os.chown(state/'global-install.json',u.pw_uid,u.pw_gid);results.append(result)
 launcher.parent.mkdir(parents=True,exist_ok=True);launcher.write_text(launcher_body);launcher.chmod(0o755)
 print(json.dumps({'installed':results,'launcher':str(launcher)},indent=2))
if __name__=='__main__':main()
