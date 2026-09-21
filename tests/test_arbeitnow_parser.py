import json

from marketradar.adapter_registry import parse
from marketradar.source_parsers import parse_arbeitnow


def test_arbeitnow_api_parser_uses_data_rows():
    body = json.dumps({
        "data": [{
            "slug": "python-engineer-123",
            "title": "Python Engineer",
            "description": "Build Python services.",
            "company_name": "Example GmbH",
            "location": "Berlin",
            "remote": True,
            "url": "https://www.arbeitnow.com/jobs/python-engineer-123",
            "tags": ["Python"],
            "job_types": ["fulltime"],
        }]
    }).encode()
    rows = parse_arbeitnow(body, "https://www.arbeitnow.com")
    assert len(rows) == 1
    assert rows[0]["title"] == "Python Engineer"
    assert rows[0]["company"] == "Example GmbH"
    assert rows[0]["remote"] is True


def test_arbeitnow_adapter_registry_is_bound():
    body = b'{"data": [{"slug":"x","title":"Python Engineer","url":"https://www.arbeitnow.com/jobs/x"}]}'
    rows = parse("arbeitnow_json", body, "https://www.arbeitnow.com/api/job-board-api?page=1", lambda _: [])
    assert len(rows) == 1
    assert rows[0]["url"].endswith("/jobs/x")
