"""PowerShell passes UTF-8 JSON through stdin, never a shell-evaluated command."""
import json,sys
args=json.load(sys.stdin)
if not isinstance(args,list) or not all(isinstance(x,str) for x in args):raise ValueError('Expected string argument array')
sys.argv=['tm',*args]
from tm_cli.main import app
app()
