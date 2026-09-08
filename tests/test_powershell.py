import json,os,pathlib,subprocess,tempfile,threading,unittest,sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=pathlib.Path(__file__).resolve().parents[1]

@unittest.skipUnless(os.name=='nt','requires Windows PowerShell')
class PowerShellContract(unittest.TestCase):
    def test_unicode_and_literal_arguments(self):
        seen=[]
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));seen.append(body)
                data=json.dumps({'status':'ok','results':[{'score':0,'text':body['query']}]}).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            def log_message(self,*a):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
        query='中文 空格 "quoted" $literal & emoji 🧠'
        try:
            for shell in ['powershell','pwsh']:
                with tempfile.TemporaryDirectory() as tmp:
                    p=pathlib.Path(tmp);cfg=p/'中文 config.toml';cfg.write_text(f'[connection]\nendpoint="http://127.0.0.1:{server.server_port}"\ncontainer="main"\n[auth]\napi_key="fixture"\n',encoding='utf-8')
                    env={**os.environ,'TM_CONFIG_FILE':str(cfg),'TM_PYTHON':sys.executable,'TM_TRANSPORT_MODE':'direct','TM_TEST_QUERY':query,'TM_ENTRY':str(ROOT/'skills/transcendence-memory/scripts/tm-search.ps1')}
                    r=subprocess.run([shell,'-NoProfile','-Command','& $env:TM_ENTRY search --json $env:TM_TEST_QUERY'],env=env,capture_output=True)
                    self.assertEqual(r.returncode,0,r.stderr.decode(errors='replace'));self.assertEqual(seen[-1]['query'],query)
        finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
