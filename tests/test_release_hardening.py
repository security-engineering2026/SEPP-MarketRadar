from pathlib import Path
import json
import sqlite3

from marketradar.release_hardening import config_gate, database_gate, filesystem_gate

ROOT=Path(__file__).resolve().parents[1]


def test_release_hardening_config_gate_is_clean():
    r=config_gate(ROOT)
    assert r['pass'], r['errors']
    assert r['source_count'] >= 500 - 0


def test_database_gate_detects_orphan_rows(tmp_path):
    from marketradar.db import connect
    db=tmp_path/'x.db'
    c=connect(db)
    c.execute("DROP TRIGGER evidence_requires_opportunity")
    c.execute("INSERT INTO evidence(opportunity_id,kind,source,url,finding,confidence,provenance_root,observed_at,evidence_hash) VALUES(?,?,?,?,?,?,?,?,?)",(999,'test','x','x','orphan',0.1,'x','t','orphan-hash'))
    c.commit(); c.close()
    result=database_gate(db)
    assert not result['pass']
    assert any(x.startswith('ORPHAN_ROWS:evidence:') for x in result['errors'])

def test_filesystem_gate_has_release_files():
    r=filesystem_gate(ROOT)
    assert r['pass'], r['errors']
