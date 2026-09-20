# SEPP-MarketRadar v4.14.0 — Deep Audit & Correction Record

## 1. Audit conclusion

The previous release was structurally stronger than earlier versions, but the source-policy model still had a material flaw: **global sources were being mixed with Iran-compatible daily sources**, and the configuration could effectively treat `Iran` as a blacklist country because the user's origin and the employer/client blacklist were conflated.

The deep pass corrected those boundaries and added regression coverage.

## 2. Source registry correction

### Before

The registry used one broad discovery/execution lane for sources whose Iran eligibility was not actually proven. Some global sources were marked `ALLOW` simply because they were global, and exact duplicate URL contracts inflated the registry.

### After

Five operational lanes are now explicit:

| Lane | Meaning |
|---|---|
| `DAILY_PROJECT_SCAN` | Source is explicitly Iran-compatible for discovery; active sources require `iran_status=ALLOW`. |
| `GLOBAL_DISCOVERY` | Global/regional source can be scanned for market intelligence, but Iran execution is not assumed. |
| `NEEDS_ANALYSIS` | Candidate requiring source-specific endpoint, terms, Iran-access, payment or runtime verification. |
| `BLOCKED_IRAN` | Source-level Iran restriction is explicit enough to prevent execution. |
| `REVIEW` | Ambiguous/manual policy review. |

Current counts: **619 total / 15 daily / 37 global discovery / 558 needs analysis / 8 blocked / 1 review**.

## 3. Iran policy bug fixed

The old default contained:

```text
execution_blacklist_countries = [Iran, Israel]
```

That is conceptually wrong for this product because Iran is the user's origin, not the employer/client country blacklist.

The corrected model is:

```text
execution_blacklist_countries = [Israel]
user_origin_country = Iran
```

Iran access is evaluated independently using source-level and opportunity-level evidence.

A source whose `country=Iran` is no longer automatically blocked.

## 4. Source-policy evidence

`ALLOW` and `BLOCK` source records now carry:

- `iran_policy_basis`
- `iran_policy_url`
- `policy_checked_at`
- `source_origin`
- `upstream_sources`

The same fields are persisted in `sources` and `source_contracts`.

## 5. Iranian source selection

The daily lane now explicitly contains:

- Jobinja
- JobVision
- IranTalent
- eEstekhdam
- Ponisha
- ParsCoders
- Karlancer
- AnjamMidam
- Typiran
- Quera
- Bale
- Eitaa
- SoroushPlus
- Kaya
- ManMitonam

The registry distinguishes **active** from **candidate** so that a source is not called live merely because its URL exists.

Kaya is represented as an **Iran-facing intermediary** with `upstream_sources=[Freelancer.com]`. This does not authorize or implement bypass of upstream restrictions.

## 6. Foreign-source treatment

The audit intentionally does **not** turn every foreign job board into `BLOCKED_IRAN` merely because it is foreign.

Three cases are separated:

1. **Platform-level restriction** → `BLOCKED_IRAN`.
2. **Global/regional discovery with uncertain Iran eligibility** → `GLOBAL_DISCOVERY` / `UNKNOWN`.
3. **Job-specific geographic restriction** → opportunity-level eligibility, not source-level blocking.

This prevents both false positives and false claims of Iran compatibility.

The current explicit source-level block list is:

`Upwork`, `Freelancer`, `Fiverr`, `PeoplePerHour`, `Toptal`, `HackerOne`, `Bugcrowd`, `Synack`.

## 7. GUI bug found and fixed

The Source Strategy double-click handler queried:

```sql
SELECT ..., notes FROM sources
```

but `sources.notes` was not a database column. The bug was invisible to the basic UI smoke test because the handler requires an interaction.

The handler now reads policy data from SQLite and notes/evidence from the immutable registry contract instead of querying a nonexistent column.

A regression test now exercises the real handler with a fake Treeview selection under Xvfb.

## 8. Duplicate-source correction

Five exact duplicate URLs were removed from the registry:

- Dice
- Landing.Jobs
- Adzuna
- Careerjet
- Talent.com

The final registry has **0 exact duplicate `base_url` values**.

Localized source instances are retained only when they represent distinct source contracts rather than exact URL duplicates.

## 9. Runtime scan correction

The scan engine now records:

- `sources_checked`
- `daily_sources_checked`
- `global_sources_checked`
- `candidates`
- `accepted_opportunities`
- `errors`

Global discovery is therefore measurable separately from Iran-compatible daily acquisition.

## 10. Validation

Observed:

- Full pytest: PASS
- Xvfb pytest: PASS
- UI smoke: PASS
- Product audit: PASS, 619 sources, 0 errors
- Release audit: PASS, 619 sources, 48 active, 0 invalid, 0 errors
- Compileall: PASS
- Production dangerous-call static scan: 0 findings
- Import graph: 37 modules, 0 cycles
- Source host-boundary audit: 0 issues
- Policy fuzz: 8,000 PASS
- Source validator fuzz: 2,000 PASS

## 11. Remaining gates

The product is **not declared finished**.

Remaining external/environment gates are:

- per-source terms review for the 49 active-source warnings
- runtime verification of individual external sources
- authorized credentials for social APIs
- real chain-specific crypto verification
- Windows EXE/installer execution on a Windows runner
- Android build execution where required

These are deliberately visible rather than hidden behind a green percentage.
