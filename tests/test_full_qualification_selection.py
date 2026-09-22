from tools.full_qualification import _select_acquisition_sample

def test_acquisition_sample_is_family_balanced_and_deterministic():
    records = [
        {"name": "z-job", "source_family": "job_board", "base_url": "https://z.example"},
        {"name": "a-job", "source_family": "job_board", "base_url": "https://a.example"},
        {"name": "b-bug", "source_family": "bug_bounty", "base_url": "https://b.example"},
        {"name": "a-social", "source_family": "social", "base_url": "https://a-social.example"},
    ]
    sample = _select_acquisition_sample(records, 3)
    assert [x["name"] for x in sample] == ["b-bug", "a-job", "a-social"]
