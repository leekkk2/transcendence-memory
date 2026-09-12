import importlib.util,json,os,pathlib,subprocess,tempfile,unittest,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('redact',ROOT/'skills/transcendence-memory/scripts/redact.py');redaction=importlib.util.module_from_spec(spec);spec.loader.exec_module(redaction)

class ClientContract(unittest.TestCase):
    def test_redaction_all_fields_and_idempotence(self):
        tokens=['hf_'+'a'*34,'glpat-'+'b'*24,'AIza'+'x'*35,'sk-'+'c'*24]
        value={'text':' '.join(tokens),'tags':tokens,'metadata':{'password':'short'},'source':'postgresql://user:secret@db/app'}
        result=redaction.redact(value);self.assertFalse(any(t in str(result) for t in tokens));self.assertNotIn('secret@',str(result));self.assertNotIn('short',str(result));self.assertEqual(result,redaction.redact(result))
        self.assertEqual(redaction.redact_text('hf_hub_download text-embedding-3-small'), 'hf_hub_download text-embedding-3-small')
        self.assertNotIn('bodysecret',redaction.redact_text('-----BEGIN PRIVATE KEY-----\nbodysecret\n-----END PRIVATE KEY-----'))
    def test_installer_complete_tree_and_conflict_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            command=[sys.executable,str(ROOT/'scripts/install.py'),'--home',tmp,'--skip-cli','--allow-dirty','--agents','codex']
            subprocess.run(command,check=True,capture_output=True)
            target=pathlib.Path(tmp)/'.agents/skills/transcendence-memory'
            self.assertTrue((target/'references/search-contract.md').exists())
            (target/'SKILL.md').write_text('local edits')
            result=subprocess.run(command,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual((target/'SKILL.md').read_text(),'local edits')
    def test_rollback_preserves_previous_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            command=[sys.executable,str(ROOT/'scripts/install.py'),'--home',tmp,'--skip-cli','--allow-dirty','--agents','codex']
            subprocess.run(command,check=True,capture_output=True)
            first=json.loads((pathlib.Path(tmp)/'.transcendence-memory/install.json').read_text())
            subprocess.run(command,check=True,capture_output=True)
            subprocess.run(command+['--rollback'],check=True,capture_output=True)
            restored=json.loads((pathlib.Path(tmp)/'.transcendence-memory/install.json').read_text())
            self.assertEqual(first,restored)
            subprocess.run(command+['--rollback'],check=True,capture_output=True)
            self.assertFalse((pathlib.Path(tmp)/'.agents/skills/transcendence-memory').exists())
    def test_bash_score_zero_and_parameters(self):
        if os.name=='nt':self.skipTest('Native Windows launchers tested separately')
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp);bin=p/'bin';bin.mkdir();cfg=p/'config.toml'
            cfg.write_text('[connection]\nendpoint="https://example.invalid"\ncontainer="main"\n[auth]\napi_key="fixture"\n')
            capture=p/'request.json'
            curl=bin/'curl';curl.write_text('#!/usr/bin/env python3\nimport sys,json,os\nbody=sys.stdin.read()\nopen(os.environ["CAPTURE"],"w").write(body)\nprint(json.dumps({"status":"ok","initialized":True,"degraded":False,"rerank_applied":True,"per_container_status":{"main":"ok"},"results":[{"score":0,"rerankScore":0,"text":"中文"}]}))\nprint("200")\n');curl.chmod(0o755)
            env={**os.environ,'PATH':str(bin)+os.pathsep+os.environ['PATH'],'TM_CONFIG_FILE':str(cfg),'CAPTURE':str(capture)}
            result=subprocess.run(['bash',str(ROOT/'skills/transcendence-memory/scripts/tm-search.sh'),'search','--rerank','--max-distance','0.8','中文'],capture_output=True,text=True,env=env)
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn('vector_distance↓=0',result.stdout);self.assertIn('rerank_relevance↑=0',result.stdout)
            body=json.loads(capture.read_text());self.assertIs(body['rerank'],True);self.assertEqual(body['score_threshold'],.8)

    def test_multi_service_node_failover_and_search_options(self):
        if os.name=='nt':self.skipTest('Native Windows launchers tested separately')
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp);bin=p/'bin';bin.mkdir();cfg=p/'config.toml'
            cfg.write_text('[connection]\nendpoints=["https://failed.invalid","https://working.invalid"]\ncontainer="main"\n[auth]\napi_key="fixture"\n')
            capture=p/'request.json'
            curl=bin/'curl';curl.write_text('#!/usr/bin/env python3\nimport sys,json,os\nurl=sys.argv[sys.argv.index("-X")+2]\nif "failed.invalid" in url:\n    sys.exit(7)\nbody=sys.stdin.read()\nopen(os.environ["CAPTURE"],"w").write(body)\nprint(json.dumps({"status":"ok","initialized":True,"degraded":False,"rerank_applied":True,"per_container_status":{"worker":"ok"},"results":[]}))\nprint("200")\n');curl.chmod(0o755)
            env={**os.environ,'PATH':str(bin)+os.pathsep+os.environ['PATH'],'TM_CONFIG_FILE':str(cfg),'CAPTURE':str(capture)}
            result=subprocess.run(['bash',str(ROOT/'skills/transcendence-memory/scripts/tm-search.sh'),'search','--container','worker','--union','多节点测试'],capture_output=True,text=True,env=env)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn("failing over to next node",result.stderr)
            body=json.loads(capture.read_text())
            self.assertEqual(body['container'],'worker')
            self.assertIs(body['union'],True)

    def test_multi_node_remember_tagging(self):
        if os.name=='nt':self.skipTest('Native Windows launchers tested separately')
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp);bin=p/'bin';bin.mkdir();cfg=p/'config.toml'
            cfg.write_text('[connection]\nendpoint="https://working.invalid"\ncontainer="main"\n[auth]\napi_key="fixture"\n')
            capture=p/'remember.json'
            curl=bin/'curl';curl.write_text('#!/usr/bin/env python3\nimport sys,json,os\nbody=sys.stdin.read()\nopen(os.environ["CAPTURE"],"w").write(body)\nprint(json.dumps({"status":"ok","object_ids":["obj-1"],"index_status":"queued"}))\nprint("200")\n');curl.chmod(0o755)
            env={**os.environ,'PATH':str(bin)+os.pathsep+os.environ['PATH'],'TM_CONFIG_FILE':str(cfg),'CAPTURE':str(capture)}
            # 1. With explicit --node
            res1=subprocess.run(['bash',str(ROOT/'skills/transcendence-memory/scripts/tm-remember.sh'),'测试节点记忆','--node','eva-node','--tags','infra'],capture_output=True,text=True,env=env)
            self.assertEqual(res1.returncode,0,res1.stderr)
            body1=json.loads(capture.read_text())
            tags1=body1['objects'][0]['tags']
            self.assertIn('node:eva-node',tags1)
            self.assertIn('infra',tags1)
            self.assertIn('node=eva-node',res1.stdout)
            # 2. With --no-node
            res2=subprocess.run(['bash',str(ROOT/'skills/transcendence-memory/scripts/tm-remember.sh'),'测试通用记忆','--no-node','--tags','infra'],capture_output=True,text=True,env=env)
            self.assertEqual(res2.returncode,0,res2.stderr)
            body2=json.loads(capture.read_text())
            tags2=body2['objects'][0]['tags']
            self.assertNotIn('node:',str(tags2))

if __name__=='__main__':unittest.main()

