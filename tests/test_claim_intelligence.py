from marketradar.claim_intelligence import (
    ClaimStatus,
    ClaimEvidence,
    EntityKind,
    EntityRef,
    build_claim,
)


def test_claim_stays_unverified_without_evidence():
    subject = EntityRef(EntityKind.CHANNEL, "telegram:example")
    claim = build_claim(subject, "HAS_COMPANION_WEBSITE", "https://example.test")
    assert claim.status is ClaimStatus.UNVERIFIED


def test_single_source_is_not_independent_confirmation():
    subject = EntityRef(EntityKind.CHANNEL, "telegram:example")
    evidence = ClaimEvidence(
        "https://t.me/example",
        "indexed_snippet",
        "2026-09-21T00:00:00Z",
        "projects: https://example.test",
    )
    claim = build_claim(
        subject,
        "HAS_COMPANION_WEBSITE",
        "https://example.test",
        [evidence],
    )
    assert claim.status is ClaimStatus.INCONCLUSIVE
    assert claim.independent_evidence_count() == 1


def test_two_independent_sources_support_claim():
    subject = EntityRef(EntityKind.CHANNEL, "telegram:example")
    evidence = [
        ClaimEvidence(
            "https://t.me/example",
            "indexed_snippet",
            "2026-09-21T00:00:00Z",
            "projects: https://example.test",
        ),
        ClaimEvidence(
            "https://example.test/about",
            "website",
            "2026-09-21T00:05:00Z",
            "official site references the channel",
        ),
    ]
    claim = build_claim(
        subject,
        "HAS_COMPANION_WEBSITE",
        "https://example.test",
        evidence,
    )
    assert claim.status is ClaimStatus.SUPPORTED


def test_contradiction_overrides_support():
    subject = EntityRef(EntityKind.COMPANY, "company:example")
    claim = build_claim(
        subject,
        "ACCEPTS_IRAN",
        "UNKNOWN",
        [
            ClaimEvidence(
                "https://example.test/policy",
                "policy",
                "2026-09-21T00:00:00Z",
            ),
            ClaimEvidence(
                "https://example.test/help",
                "help",
                "2026-09-21T00:01:00Z",
            ),
        ],
    )
    assert claim.status is ClaimStatus.SUPPORTED
    assert claim.evaluate(contradictory=True) is ClaimStatus.CONTRADICTED
