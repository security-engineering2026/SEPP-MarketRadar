from marketradar.federation import AcquisitionFallback


def test_fallback_records_provider_provenance_and_confidence():
    calls=[]
    def primary(source,url):
        calls.append('primary')
        raise TimeoutError('primary down')
    def secondary(source,url):
        calls.append('secondary')
        return {'status':200,'body':b'payload','url':url}
    result=AcquisitionFallback([
        {'name':'primary','fetch':primary,'confidence_multiplier':1.0},
        {'name':'secondary','fetch':secondary,'confidence_multiplier':0.8},
    ]).fetch({'name':'demo'},'https://example.test/data')
    assert calls == ['primary','secondary']
    assert result['acquisition_provider']=='secondary'
    assert result['fallback_used'] is True
    assert result['confidence_multiplier']==0.8
    assert result['attempts_meta'][0]['status']=='PROVIDER_FAILURE'


def test_fallback_distinguishes_source_unavailable_from_provider_failure():
    def missing(source,url):
        return {'status':404,'body':b''}
    try:
        AcquisitionFallback([{'name':'missing','fetch':missing}]).fetch({'name':'demo'},'https://example.test/data')
        assert False, 'expected source unavailable'
    except RuntimeError as exc:
        assert str(exc)=='SOURCE_UNAVAILABLE'

    def broken(source,url):
        raise TimeoutError('network')
    try:
        AcquisitionFallback([{'name':'broken','fetch':broken}]).fetch({'name':'demo'},'https://example.test/data')
        assert False, 'expected provider failure'
    except RuntimeError as exc:
        assert str(exc)=='ALL_ACQUISITION_PROVIDERS_FAILED'
