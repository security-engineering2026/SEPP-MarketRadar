import json
from pathlib import Path
import pytest
from marketradar.source_registry import load_source_records


def test_registry_has_explicit_source_lifecycle_metadata():
    rows = load_source_records(Path(__file__).parents[1] / 'config' / 'sources.json')
    target=json.loads((Path(__file__).parents[1] / 'config' / 'source_targets.json').read_text())['target_registered_sources']
    assert len(rows) >= 5 and target >= 500
    assert all(r['verification_state'] in {'unverified','documented','verified','degraded','blocked'} for r in rows)
    assert all(r['access_scope'] in {'public','local'} or r['access_scope'] for r in rows)
    documented = [r for r in rows if r['verification_state'] == 'documented']
    assert len(documented) >= 5


def test_registry_rejects_missing_allow_hosts(tmp_path):
    p=tmp_path/'sources.json'
    p.write_text(json.dumps([{'name':'A','base_url':'https://example.com','adapter':'json'}]), encoding='utf-8')
    with pytest.raises(ValueError, match='SOURCE_ALLOW_HOSTS_REQUIRED'):
        load_source_records(p)
