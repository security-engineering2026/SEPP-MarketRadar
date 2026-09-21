from marketradar.access_broker import AccessMode, connector_setup_message, plan_for_url
from marketradar.tor_transport import TorAccessError, validate_onion_url


def test_restricted_platforms_produce_connector_plan_without_bypass():
    p = plan_for_url("https://www.linkedin.com/jobs/view/123")
    assert p.mode is AccessMode.PUBLIC_INDEX
    assert not p.execution_allowed
    assert "explicit crawl permission" in p.required_action


def test_authorized_telegram_scope_is_explicit_and_not_bulk_by_default():
    p = plan_for_url(
        "https://t.me/example_channel",
        {"telegram": {"mode": "OFFICIAL_API", "scope": "@example_channel", "execution_allowed": False}},
    )
    assert p.mode is AccessMode.OFFICIAL_API
    assert p.scope == "@example_channel"
    assert not p.bulk_collection_allowed


def test_setup_wizard_signal_is_actionable():
    result = connector_setup_message("https://www.instagram.com/example/")
    assert result["required"] is True
    assert result["next_step"] == "OPEN_ACCESS_WIZARD"


def test_onion_transport_requires_explicit_known_address():
    assert validate_onion_url("http://example" + ".onion") == "http://example.onion"
    try:
        validate_onion_url("https://example.com/")
    except TorAccessError as exc:
        assert str(exc) == "ONION_URL_REQUIRED"
    else:
        raise AssertionError("non-onion URL was accepted")
