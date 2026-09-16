import importlib.util
import json
from pathlib import Path
import pytest

SCRIPT = Path(__file__).parents[1] / 'skills/transcendence-memory/scripts/tm-incremental-graphify.py'

def load(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('graphify_test', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, 'LEDGER_FILE', tmp_path / 'ledger.json')
    return mod

def test_corrupt_ledger_never_starts_fresh(tmp_path, monkeypatch):
    mod = load(tmp_path, monkeypatch)
    mod.LEDGER_FILE.write_text('{broken')
    with pytest.raises(ValueError): mod.load_ledger()

def test_large_item_cards_are_bounded_without_losing_text(tmp_path, monkeypatch):
    mod = load(tmp_path, monkeypatch)
    text = 'Aster sensor works. ' * 700
    cards = mod.cluster_memories([{'id':'one', 'text':text, 'tags':['sop']}])
    assert len(cards) > 1
    assert max(len(c['text']) for c in cards) <= 3500
    assert ''.join(c['source_text'] for c in cards) == text

def test_http_source_uses_canonical_and_checks_pages(tmp_path, monkeypatch):
    mod = load(tmp_path, monkeypatch)
    calls=[]
    def api(endpoint, key, path, **kwargs):
        calls.append(path)
        return {'items':[{'id':'one','text':'safe'}], 'total':1}
    monkeypatch.setattr(mod,'api_call',api)
    rows=mod.get_container_memories('canonical', endpoint='https://example.org', api_key='test')
    assert rows[0]['id']=='one'
    assert calls==['/containers/canonical/memories?limit=500&offset=0']

def test_ledger_endpoint_isolation(tmp_path, monkeypatch):
    mod=load(tmp_path,monkeypatch)
    ledger=mod.load_ledger('https://one.example')
    mod.save_ledger(ledger)
    with pytest.raises(ValueError, match='endpoint'):mod.load_ledger('https://two.example')

def test_lock_blocks_second_writer(tmp_path, monkeypatch):
    mod=load(tmp_path,monkeypatch)
    with mod.ledger_lock():
        with pytest.raises(RuntimeError, match='locked'):
            with mod.ledger_lock():pass

def test_target_rows_skip_removed_and_deduplicate(tmp_path,monkeypatch):
    mod=load(tmp_path,monkeypatch)
    aliases={'alias':'real'}
    rows=[{'name':'alias'},{'name':'real'},{'name':'gone'},{'name':'__manifest'}]
    assert mod.target_containers(rows,aliases,{'gone'})==['real']

def test_changed_content_gets_new_fingerprint(tmp_path,monkeypatch):
    mod=load(tmp_path,monkeypatch)
    assert mod.memory_fingerprint({'id':'x','text':'before'}) != mod.memory_fingerprint({'id':'x','text':'after'})

def test_status_failure_returns_nonzero(tmp_path,monkeypatch):
    mod=load(tmp_path,monkeypatch)
    def api(endpoint,key,path,**kw):
        if path=='/containers':return {'containers':[{'name':'a'}]}
        raise RuntimeError('unavailable')
    monkeypatch.setattr(mod,'api_call',api)
    assert mod.status('https://example.org','test',{},set(),mod.load_ledger())==1


def test_pending_job_resumes_without_resubmit(tmp_path,monkeypatch):
    mod=load(tmp_path,monkeypatch)
    item={'id':'one','text':'safe'}
    card=mod.cluster_memories([item])[0]
    ledger=mod.load_ledger('https://example.org')
    ledger['containers']['c']={'cards':{card['content_hash']:{'state':'pending','pid':9}}}
    monkeypatch.setattr(mod,'get_container_memories',lambda *a,**kw:[item])
    monkeypatch.setattr(mod,'api_call',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('must not resubmit')))
    monkeypatch.setattr(mod,'wait_for_job',lambda *a,**kw:None)
    mod.process_container('https://example.org','k',ledger,'c',dry_run=False,input_file=None,budget=[1],max_chars=50000,wait_seconds=10)
    assert ledger['containers']['c']['cards'][card['content_hash']]['state']=='done'


def test_existing_graph_requires_reconciliation(tmp_path,monkeypatch):
    mod=load(tmp_path,monkeypatch)
    monkeypatch.setattr(mod,'get_container_memories',lambda *a,**kw:[{'id':'x','text':'safe'}])
    monkeypatch.setattr(mod,'api_call',lambda *a,**kw:{'node_count':1})
    with pytest.raises(RuntimeError,match='baseline'):
        mod.process_container('https://example.org','k',mod.load_ledger(),'c',dry_run=False,input_file=None,budget=[1],max_chars=50000,wait_seconds=10)
