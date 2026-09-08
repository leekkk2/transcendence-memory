"""PowerShell passes UTF-8 JSON through stdin, never a shell-evaluated command."""
import base64,io,json,sys
wire=sys.stdin.buffer.read().decode('utf-8-sig').strip()
if wire.startswith('TM_ARGS_V1:'):
    wire=base64.b64decode(wire.split(':',1)[1],validate=True).decode('utf-8')
args=json.loads(wire)
if isinstance(args,dict):
    payload=args
    if not isinstance(payload.get('stdin'),str):raise ValueError('Expected token input string')
    sys.stdin=io.StringIO(payload['stdin'].lstrip('\ufeff'))
    args=payload['args']
if not isinstance(args,list) or not all(isinstance(x,str) for x in args):raise ValueError('Expected string argument array')
sys.argv=['tm',*args]
from tm_cli.main import app
app()
