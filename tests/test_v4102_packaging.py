from pathlib import Path

def test_windows_build_smoke_is_disposable_and_release_tree_stays_clean():
    script=(Path(__file__).parents[1]/'packaging'/'build_windows.ps1').read_text(encoding='utf-8')
    assert 'SEPP-MarketRadar-Smoke-' in script
    assert 'Portable artifact contains runtime data' in script
    assert 'Portable artifact contains runtime logs' in script

def test_installer_excludes_portable_marker():
    text=(Path(__file__).parents[1]/'packaging'/'installer.iss').read_text(encoding='utf-8')
    assert 'Excludes: ".portable"' in text


def test_runtime_data_root_can_be_overridden_for_isolation():
    from marketradar.paths import writable_root
    assert writable_root().exists()
    assert 'marketradar-runtime' in str(writable_root())
