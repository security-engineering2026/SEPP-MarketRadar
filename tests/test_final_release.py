from marketradar.final_readiness import _local_lifecycle, _check_backup_restore
from marketradar.db import connect


def test_final_economic_lifecycle_is_complete():
    c = connect(':memory:')
    try:
        result = _local_lifecycle(c)
        assert result['state_after_claim'] == 'DELIVERED'
        assert result['final_state'] == 'PAID'
    finally:
        c.close()


def test_final_backup_restore_roundtrip():
    result = _check_backup_restore()
    assert result['restored_value'] == 'ok'
    assert len(result['sha256']) == 64
