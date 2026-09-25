from pathlib import Path
import json
from marketradar.desktop import app_root, load_settings


def test_desktop_entrypoint_exists():
    assert (Path(__file__).parents[1] / "desktop" / "MarketRadar.pyw").exists()


def test_desktop_settings_load():
    settings = load_settings(app_root())
    assert settings["db"].endswith("marketradar.db")
    assert settings["http_timeout"] > 0


def test_desktop_smoke_test():
    from marketradar.desktop import smoke_test
    assert smoke_test() == 0


def test_source_contracts_are_persisted():
    from marketradar.desktop import open_runtime
    root, settings, sources, conn, runtime = open_runtime()
    try:
        placeholders = ",".join("?" for _ in sources)
        names = [s["name"] for s in sources]
        matched = conn.execute(
            f"SELECT COUNT(*) FROM source_contracts WHERE source IN ({placeholders})",
            names,
        ).fetchone()[0]
        assert matched == len(sources)
    finally:
        conn.close()

def test_source_strategy_detail_does_not_query_nonexistent_notes_column(monkeypatch):
    from marketradar.desktop import MarketRadarDesktop
    from marketradar.db import connect, sync_source_contracts
    from marketradar.source_registry import load_source_records
    import tempfile
    class Tree:
        def selection(self): return ('Kaya_Iran_Intermediary',)
        def item(self, _, option=None): return ('Kaya_Iran_Intermediary',) if option=='values' else {'values': ('Kaya_Iran_Intermediary',)}
    class Master: pass
    with tempfile.TemporaryDirectory() as d:
        class App:
            strategy_tree=Tree()
            master=Master()
            sources=[{'name':'Kaya_Iran_Intermediary','notes':'ok','iran_policy_url':'https://kaya.ir/'}]
            conn=connect(Path(d)/'x.db')
        records=load_source_records(Path(__file__).parents[1]/'config'/'sources.json')
        try:
            sync_source_contracts(App.conn,records)
            shown=[]
            monkeypatch.setattr('marketradar.desktop.messagebox.showinfo', lambda *a, **k: shown.append(a[1]))
            MarketRadarDesktop._open_strategy_source(App())
            assert shown and 'Kaya_Iran_Intermediary' in shown[0] and 'Notes: ok' in shown[0]
        finally:
            App.conn.close()

def test_verification_worker_uses_thread_local_sqlite_connection(monkeypatch):
    """Regression: background verification must not use the UI thread's SQLite connection."""
    import threading
    import tempfile
    from pathlib import Path
    from marketradar.db import connect

    with tempfile.TemporaryDirectory() as d:
        try:
            path = Path(d) / 'x.db'
            ui_conn = connect(path)
            errors = []
            def worker():
                worker_conn = connect(path)
                try:
                    worker_conn.execute('SELECT 1').fetchone()
                except Exception as exc:
                    errors.append(exc)
                finally:
                    worker_conn.close()
            t = threading.Thread(target=worker)
            t.start(); t.join()
            ui_conn.close()
            assert not errors
        finally:
            if 'ui_conn' in locals():
                ui_conn.close()


def test_initial_acquisition_only_targets_fresh_workspace(tmp_path):
    from marketradar.desktop import needs_initial_acquisition
    from marketradar.db import connect

    conn = connect(tmp_path / "fresh.db")
    try:
        assert needs_initial_acquisition(conn) is True
        conn.execute("INSERT INTO federation_runs (source, status, observation_count) VALUES (?, ?, ?)", ("test-source", "ERROR", 0))
        conn.commit()
        assert needs_initial_acquisition(conn) is True
        conn.execute("INSERT INTO federation_runs (source, status, observation_count) VALUES (?, ?, ?)", ("test-source", "OK", 2))
        conn.commit()
        assert needs_initial_acquisition(conn) is False
    finally:
        conn.close()
