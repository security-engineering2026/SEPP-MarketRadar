from marketradar.discovery_intelligence import QueryPlanner

def test_priority_region_boost_applied_once():
    config = {
        "queries": [],
        "priority_queries": [],
        "country_templates": [{"family": "jobs", "template": "jobs"}],
        "priority_regions": [{"country": "Iran", "priority_boost": 5.0}],
    }
    plans = QueryPlanner(config).plan(
        [{"country": "Iran", "region": "Iran", "language": "fa", "iso2": "IR"}],
        max_queries=50,
    )
    assert plans
    assert plans[0]["operator_score"] == 5.10
