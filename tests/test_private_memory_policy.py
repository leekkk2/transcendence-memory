import subprocess
from pathlib import Path

ROOT=Path(__file__).parents[1]

def test_explicit_private_policy_preserves_sensitive_text(tmp_path):
    config=tmp_path/'config.toml'
    config.write_text('[privacy]\npreserve_sensitive = true\n')
    redactor=ROOT/'skills/transcendence-memory/scripts/redact.py'
    import os
    env={**os.environ,'TM_CONFIG':str(config)}
    r=subprocess.run(['python3',str(redactor),'--memory'],input='password=synthetic-private-value',text=True,capture_output=True,env=env)
    assert r.returncode==0
    assert r.stdout=='password=synthetic-private-value'

def test_default_redaction_is_preserved(tmp_path):
    import os
    config=tmp_path/'config.toml';config.write_text('')
    r=subprocess.run(['python3',str(ROOT/'skills/transcendence-memory/scripts/redact.py'),'--memory'],input='password=synthetic-private-value',text=True,capture_output=True,env={**os.environ,'TM_CONFIG':str(config)})
    assert 'synthetic-private-value' not in r.stdout
