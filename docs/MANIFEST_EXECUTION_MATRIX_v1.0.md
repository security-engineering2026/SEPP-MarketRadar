# Manifest Execution & Evidence Matrix v1.0

Status: **normative execution register derived from `docs/MANIFEST.md`**.
Baseline: **SEPP-MarketRadar v16.1.2**.
Branch: `qualification/windows-verification-hardening`.
Purpose: تبدیل 49 قرارداد Manifest به واحدهای قابل‌پیاده‌سازی، قابل‌آزمون و قابل‌اثبات. این جدول مرجع اجرایی است؛ GitHub فقط یکی از محیط‌های اثبات است.

## قواعد وضعیت

- **PASS** = کد + تست مرتبط + شواهد محیط لازم + ثبت وضعیت، مطابق Definition of Done.
- **OPEN** = بخشی از پیاده‌سازی/تست/شواهد موجود است ولی برای PASS کامل نیست.
- **FAIL** = تست در محیط مناسب اجرا شده و معیار پذیرش را رد کرده است.
- **NOT EXECUTED** = آزمون مشخص شده ولی هنوز اجرا نشده است.
- **SKIPPED** = عمداً و با دلیل مستند اجرا نشده است.
- وجود کد یا تست به‌تنهایی PASS نیست.
- «راه‌حل موجود» یعنی در همین repo یا یکی از repoهای مرجع داخلی راه‌حل قابل استفاده دیده شده؛ این با اثبات نهایی یکسان نیست.
- «مرجع بیرونی» فقط زمانی «بله» است که برای آن قرارداد منبع فنی معتبر بررسی/ثبت شده باشد؛ برای تعریف Domain، Manifest مرجع اول و حاکم است.

## مسیر اجباری

`MANIFEST → OUTPUT → GOAL → EVIDENCE → TEST → ENVIRONMENT → REUSE → EXECUTE → FAILURE EXTRACTION → ROOT CAUSE → MINIMAL PATCH → REGRESSION → QUALIFICATION → MANIFEST RECONCILIATION`

## ماتریس اجرایی

| # | Manifest | آنچه باید پیاده/کدنویسی شود | آزمون/معیار پذیرش | وضعیت فعلی | موارد حل‌نشده / بررسی راه‌حل | رجوع به منابع بیرونی | اولویت | محیط اثبات |
|---|---|---|---|---|---|---|---|---|
| 1 | Mission | pipeline کامل Market Observation تا Learning؛ مرزبندی acquisition/domain/decision/action/outcome | E2E زنجیره؛ هر transition دارای evidence/audit | OPEN | معماری موجود؛ E2E کامل و محصولی هنوز qualification نشده | بله—architecture/testing guidance؛ Manifest مرجع Domain | P0 | Linux CI + Windows |
| 2 | Core truth model | مدل‌های WORLD/OBSERVATION/SNAPSHOT/EVIDENCE/CLAIM/STATE/DECISION/ACTION/OUTCOME/LEARNING و UNKNOWN | جلوگیری از تبدیل observation به truth/authority؛ UNKNOWN propagation؛ replay | OPEN | بخش عمده موجود؛ تست cross-layer کامل لازم | محدود؛ Domain از Manifest | P0 | Python CI + Windows |
| 3 | Domain contract | identity/state/timestamp/provenance/version برای Source…LearningSignal | schema/constraint/migration + round-trip + integrity | OPEN | مدل‌ها موجود؛ audit هر object و migration matrix لازم | بله—SQLite/Python docs برای persistence | P0 | Linux CI + Windows |
| 4 | Source registry | registry با stateهای discovered/documented/verified/degraded/blocked/dead/archived/execution-eligible و شمارش تفکیک‌شده | state transition، count truthfulness، عدم نمایش count به‌عنوان integration | OPEN | registry موجود؛ runtime qualification و reporting E2E لازم | بله—HTTP/source tooling docs؛ Domain از Manifest | P0 | Linux CI + Windows + live Internet |
| 5 | Source adapter contract | adapter/method/endpoints/I-O/auth/policy/limits/parser/failure/evidence/capability fields | schema completeness؛ adapter contract validation؛ missing-field rejection | OPEN | contract موجود؛ همه adapterها باید audit شوند | بله—library/API docs برای adapterهای واقعی | P0 | Linux CI + Windows |
| 6 | Capability maturity | ladder کامل REGISTERED→…→EXECUTION_READY، promotion evidence، stale/revalidation | monotonicity، anti-downgrade، evidence-bound promotion | **PASS** | regression و Windows CI #230 ثبت شده | بله—API/tool docs در صورت adapter-specific | P0 | Python CI + Windows CI |
| 7 | Source verification | HTTP/parse/policy/eligibility/KYC/payment/terms/timestamp/confidence/failure/stale | positive/negative/stale/revalidation/contradiction cases | OPEN | verification موجود؛ live-source qualification ناقص | بله—HTTP/API docs + source terms | P0 | Windows + live Internet |
| 8 | Discovery | catalog/search/public pages/communities/project URLs → candidates + provenance فقط | discovery never grants authority؛ provenance retained | OPEN | discovery موجود؛ breadth/live verification ناقص | بله—search/catalog APIs و OSS | P1 | Linux CI + live Internet |
| 9 | Acquisition | source/host/size/timeout/retry/redirect policy + secret isolation | SSRF/private-IP, redirect boundary, size/timeout/retry, secret leakage | OPEN | controls موجود؛ adversarial + live network qualification لازم | بله—HTTP client/security docs | P0 | Linux CI + Windows + sandbox Internet |
| 10 | Immutable raw evidence | raw payload hash/replay؛ snapshot identity source+endpoint+time+digest | byte/hash replay، tamper detection، deterministic snapshot ID | OPEN | storage/hash موجود؛ complete tamper/replay qualification لازم | بله—Python hashing docs | P0 | Python CI + Windows |
| 11 | Observation layer | preserve source/url/time/HTTP/content-type/digest/provenance | round-trip + immutable metadata + malformed response handling | OPEN | implementation موجود؛ full negative suite لازم | بله—HTTP library docs | P0 | Linux CI + Windows |
| 12 | Canonical opportunity | normalize observations without losing origin/contradictions | source links retained؛ contradiction preserved؛ deterministic normalization | OPEN | pipeline موجود؛ E2E evidence graph qualification لازم | بله—normalization/library docs where used | P0 | Linux CI + Windows |
| 13 | Deduplication | stable identity + observation history; conflict retention | duplicate/conflict/identity-change tests; no destructive merge | OPEN | dedup موجود؛ adversarial history tests لازم | محدود؛ Domain از Manifest | P0 | Python CI + Windows |
| 14 | Entity resolution | MATCH/POSSIBLE_MATCH/NO_MATCH + confidence/evidence؛ conservative reversible merge | threshold, non-merge, idempotency, audit tests | OPEN | راه‌حل و regression موجود؛ runtime qualification کامل این contract هنوز جداگانه ثبت نشده | بله—similarity algorithm docs اگر لازم | P0 | Python CI + Windows |
| 15 | Party resolution | role-separated client/employer/agency/buyer/procurement/intermediary + temporal relations | role collision, temporal validity, provenance | OPEN | مدل موجود؛ complete scenario suite لازم | محدود؛ Manifest مرجع | P0 | Python CI + Windows |
| 16 | Evidence graph | source→observation→evidence→claim→domain object؛ claim-level provenance | orphan prevention، evidence linkage، consequential claim trace | OPEN | claim provenance fix موجود؛ full graph E2E لازم | محدود؛ Manifest مرجع | P0 | Python CI + Windows |
| 17 | Trust/reputation | provenance diversity, manipulation signals, confidence, UNKNOWN | insufficient evidence => UNKNOWN؛ trust ≠ evidence confidence | OPEN | assessment موجود؛ adversarial/coverage tests لازم | بله—reputation/OSINT methodology docs در صورت استفاده | P1 | Python CI + live Internet |
| 18 | Eligibility | مستقل از payment/KYC/health/ranking؛ ALLOW/REVIEW/BLOCK/UNKNOWN | matrix independence؛ UNKNOWN never ALLOW؛ regression | OPEN | code موجود؛ cross-policy matrix باید کامل شود | محدود؛ Manifest مرجع | P0 | Python CI + Windows |
| 19 | Payment intelligence | claimed/documented/observed/verified separation | false payment verification rejection؛ provenance/state transitions | OPEN | payment intelligence موجود؛ external evidence qualification لازم | بله—payment provider/API docs | P0 | Linux CI + credentialed endpoint |
| 20 | KYC intelligence | KYC جدا از eligibility/payment؛ UNKNOWN→REVIEW/UNKNOWN | no implicit allow؛ state transition tests | OPEN | code موجود؛ external-provider cases لازم | بله—provider/terms docs | P0 | Linux CI + external endpoint |
| 21 | Policy engine | deterministic/versioned/auditable BLOCK/REVIEW/EXECUTE/UNKNOWN | same input+version => same output؛ evidence/version binding | OPEN | policy.v1 موجود؛ complete policy corpus + CI evidence لازم | محدود؛ Manifest مرجع | P0 | Python CI + Windows |
| 22 | Temporal/change intelligence | first_seen/last_seen/freshness/expiry/revalidation/contradiction ledger | immutable contradiction records؛ stale detection؛ revalidation | **PASS** | runtime regression ثبت شده در Windows CI #230 | بله—time/date library docs در صورت نیاز | P0 | Python CI + Windows |
| 23 | Intelligence | classify/summarize/cluster/demand/competition/TTM/signals without authority | analytical output traceability؛ no authorization privilege | OPEN | components موجود؛ adversarial decision-boundary tests لازم | بله—ML/algorithm docs where used | P1 | Python CI + Windows |
| 24 | Ranking | ranking جدا از policy/decision؛ factors/confidence؛ cannot override hard constraints | BLOCK/UNKNOWN cannot be promoted by score؛ factor explainability | OPEN | ranking موجود؛ full invariant suite لازم | بله—ranking/math docs if algorithm-specific | P0 | Python CI + Windows |
| 25 | Decision model | domain+evidence+policy+ranking+profile → reproducible decision snapshot | deterministic replay؛ immutable snapshot؛ trace | **PASS** | decision trace regression ثبت شده در Windows CI #230 | محدود؛ Manifest مرجع | P0 | Python CI + Windows |
| 26 | Daily Intelligence Center | Top-7/Do-Now/monitor/blocked/unknown as views over decision model | bucket correctness؛ snapshot digest؛ no execution authority | OPEN | DAILY_SNAPSHOT trace موجود و تست شده؛ full UI/product evidence لازم | بله—UI/testing docs | P1 | Python CI + Windows UI |
| 27 | Human approval | explicit approval exact-action bound; low-risk exception only by policy | target/action/params/evidence/policy binding؛ reject mismatch | OPEN | approval broker موجود؛ full Windows UI/action flow لازم | محدود؛ Manifest مرجع | P0 | Windows |
| 28 | Authorization broker | target/action/params digest/evidence digest/policy/expiry/nonce; fail-closed | replay, expiry, tamper, mismatch, used nonce | OPEN | broker موجود؛ regression موجود but complete product qualification needed | بله—crypto/security library docs | P0 | Python CI + Windows |
| 29 | Action model | preconditions/execution/result/audit/failure/idempotency/external ref | retry/idempotency/failure/replay/external-result tests | OPEN | workflow/idempotency موجود؛ full execution environment missing | بله—HTTP/API idempotency docs | P0 | Windows + sandbox/external endpoint |
| 30 | Application lifecycle | discovery→application→negotiation→acceptance→delivery→payment valid transitions | invalid transition fail-closed; audit; replay | OPEN | lifecycle موجود؛ site-specific adapters/external submission evidence missing | بله—platform/API docs | P0 | Windows + credentialed external |
| 31 | Delivery | immutable artifact evidence/digest/actor/time | artifact tamper, digest mismatch, actor/time integrity | OPEN | delivery model موجود؛ real delivery evidence not qualified | بله—artifact/storage docs | P0 | Windows + external endpoint |
| 32 | Revenue/payment | claim vs recording vs explicit verified PAID; duplicate reference rejection | duplicate payment ref; false PAID rejection; evidence-bound settlement | OPEN | finance module موجود؛ real payment verification missing | بله—payment provider docs | P0 | Linux CI + credentialed endpoint |
| 33 | Outcome ledger | immutable submission/response/accept/reject/cancel/delivery/payment outcomes | append-only, ordering, replay, mutation rejection | OPEN | ledger موجود؛ full E2E outcome cycle missing | محدود؛ Manifest مرجع | P0 | Python CI + Windows |
| 34 | Market learning | learn from outcomes/source/party/pricing/TTM/acceptance/revenue without rewriting history | historical immutability + deterministic learning inputs | OPEN | learning modules موجود؛ long-path E2E لازم | بله—analytics/ML docs where used | P1 | Linux CI + Windows |
| 35 | Negative/rejection intelligence | rejected/blocked/expired/failed as first-class signals + reasons | reason preservation; future policy/ranking/learning consumption | OPEN | rejection data present؛ closed-loop learning test لازم | محدود؛ Manifest مرجع | P1 | Python CI + Windows |
| 36 | Acquisition fallback | provider chain/provenance/confidence + SOURCE_UNAVAILABLE vs ALL_PROVIDERS_FAILED | ordering, provenance, fallback flag, distinct failures | **PASS** | implementation + regression + Windows CI #230 evidence موجود | بله—HTTP provider docs | P0 | Python CI + Windows + Internet |
| 37 | Scheduler/runtime | durable/resumable scans; retry/backoff/timeout/stale/recovery | crash/restart, duplicate prevention, stale recovery, observability | OPEN | scheduler/runtime exists؛ Windows runtime drill لازم | بله—scheduler/runtime library docs | P0 | Windows + Linux CI |
| 38 | Security | host allowlist, SSRF/private IP, secret isolation, bound approvals, replay, immutable ledgers, least privilege | adversarial security suite + negative tests + secret scan | OPEN | major controls موجود؛ complete adversarial qualification لازم | بله—official security docs + security libraries | P0 | Linux CI + Windows + isolated sandbox |
| 39 | Windows product | real portable EXE + installer; product authority on Windows | build, launch, filesystem, install/uninstall, clean-machine smoke, artifact hash | OPEN | packaging path exists; previous qualification had failures; new complete post-audit run absent | بله—PyInstaller official docs؛ Windows build must run on Windows | P0 | **Windows self-hosted** |
| 40 | Android companion | review/notification/approval/status only; no independent authority | assemble + emulator E2E + authority-boundary tests | **PASS** | Full Qualification #209 Android assemble/E2E PASS; later #211 environment failure retained separately | بله—Android Emulator official docs | P1 | Ubuntu CI + Android emulator |
| 41 | Observability | status/time/error/retry/health/digest + attempted/success/fail/skipped/unknown/not-configured metrics | metric/state correctness; error/retry traceability | OPEN | observability exists; full operational E2E evidence needed | بله—logging/metrics docs | P1 | Python CI + Windows |
| 42 | Auditability | immutable audit trail for consequential changes; reject silent mutation/deletion | mutation rejection, trace completeness, replay | OPEN | audit/ledgers exist; comprehensive cross-module audit test needed | محدود؛ Manifest مرجع | P0 | Python CI + Windows |
| 43 | Data integrity | FK/unique/constraints/hashes/idempotency/transactions/reconstructability | migration, rollback, corruption, duplicate, FK/constraint tests | OPEN | SQLite persistence/migrations exist; exhaustive integrity matrix needed | بله—Python sqlite3 official docs | P0 | Linux CI + Windows |
| 44 | Product UI | expose source/evidence/confidence/eligibility/policy/ranking/approval/action/outcome; UNKNOWN/REVIEW/BLOCKED not ready | UI state matrix + visual smoke + accessibility/basic interaction | OPEN | UI structure exists; Windows visual/product qualification incomplete | بله—UI framework docs | P0 | Windows UI |
| 45 | Reporting truthfulness | registered/discovered/verified/execution-ready labels; evidence-backed claims | report count reconciliation against registry; no unsupported production/live claims | OPEN | reporting controls exist; end-to-end reconciliation required | محدود؛ Manifest مرجع | P0 | Python CI + Windows |
| 46 | Definition of done | enforce code + regression + adversarial + env evidence + audit exposure + no legacy contradiction | meta-test/checklist preventing completion without evidence | OPEN | rule documented; automated enforcement/qualification gate must be proven | بله—GitHub Actions workflow docs | P0 | GitHub CI + Windows |
| 47 | Manifest governance | map every new capability to existing contract or explicit amendment; no silent domain redefinition | manifest mapping check; amendment detection; audit consistency | **PASS (governance)** | framework registered; automated enforcement can be strengthened | بله—GitHub/version-control docs | P0 | GitHub CI |
| 48 | Development rule | enforce MANIFEST→AUDIT→GAP→PATCH→TEST→CI→AUDIT update workflow | process/audit consistency; no feature marked complete without evidence | **PASS (process)** | currently documented; should become machine-checkable where possible | بله—GitHub Actions docs | P0 | GitHub CI |
| 49 | Final architecture | preserve distinctions between happened/observed/believed/allowed/approved/executed/outcome | full end-to-end provenance/replay/authority-boundary test | OPEN | architecture exists; complete E2E proof is the final integration gate | محدود؛ Manifest مرجع | P0 | Linux CI + Windows |

## 1. اولویت اجرایی

### P0 — قفل‌کننده محصول
1. 39 Windows product qualification
2. 46 Definition of Done enforcement
3. 49 Final architecture E2E proof
4. 38 Security adversarial qualification
5. 28 Authorization broker
6. 27 Human approval
7. 29 Action model
8. 30 Application lifecycle
9. 31 Delivery
10. 32 Revenue/payment
11. 33 Outcome ledger
12. 37 Scheduler/runtime
13. 43 Data integrity
14. 44 Product UI
15. 45 Reporting truthfulness
16. 1–25 core truth/evidence/policy/decision contracts that feed the action path

### P1 — پس از قفل P0
- Discovery breadth
- Trust/reputation
- Intelligence/TTM/market signals
- Daily Intelligence Center product qualification
- Market learning / negative intelligence
- Observability hardening
- Android companion refinements

## 2. محیط اثبات اجباری

- **Python/Linux CI:** unit, regression, migration, deterministic domain contracts, static/compile checks.
- **Windows self-hosted:** EXE, installer, install/uninstall, filesystem/registry/ACL/process/UI/runtime semantics, Windows product smoke.
- **Live Internet / isolated network:** source reachability, acquisition, redirect policy, source health and dynamic browser.
- **Credentialed external endpoint:** real platform authentication/application/payment observations.
- **Ubuntu + Android emulator:** Android assemble/E2E. Android Emulator is an official supported environment for testing device/API variations. citeturn1search3turn1search7
- **GitHub Actions:** workflow/manifest/static contracts and durable evidence aggregation. Independent jobs can run in parallel when dependencies do not force ordering; matrices can fan out tests. citeturn0search3turn0search8

For Windows packaging, the build must execute on Windows; PyInstaller explicitly is not a cross-compiler, and its documentation recommends validating one-folder output before one-file packaging because diagnosis is easier there. citeturn0search9turn0search4

## 3. Reuse register

Before new implementation, inspect in this order:

1. **SEPP-MarketRadar** existing code/tests.
2. **CDR_Core** solved patterns.
3. **Software_Forge** durable transfer/continuity/release-state patterns.
4. Official Python/SQLite/Android/GitHub/PyInstaller documentation.
5. Mature OSS implementation.
6. New code only when no adequate solution exists.

Known reusable internal solutions already relevant:
- capability ladder + anti-downgrade;
- claim-level provenance;
- entity MATCH/POSSIBLE_MATCH/NO_MATCH;
- acquisition fallback;
- immutable decision traces;
- daily snapshot trace;
- Software_Forge durable transfer/continuity/release-state patterns;
- Windows Python resolver/bootstrap pattern.

## 4. Evidence discipline

A row is not PASS merely because:
- a file exists;
- a function exists;
- pytest exists;
- source inspection looks correct;
- a GitHub job is queued;
- another environment passed.

The evidence must belong to the environment that proves the claim.

GitHub Actions security guidance recommends pinning Actions to full-length commit SHAs; this matrix therefore treats workflow supply-chain alignment as an evidence item rather than a prose assumption. citeturn1search0turn1search11

## 5. Current snapshot

- Manifest contracts: **49**
- Explicit runtime/qualification PASS in the current audit: **5 product/technical contracts** (6, 22, 25, 36, 40)
- Governance/process PASS: **2** (47, 48)
- Other contracts: **OPEN** pending complete implementation/test/environment evidence.
- Known explicit post-audit product gaps: **Windows product qualification** and **full post-audit qualification evidence**.
- This matrix deliberately does **not** convert “code aligned by inspection” into PASS.

## 6. Mandatory update rule

Every future implementation cycle MUST update this matrix in the same change set or immediately after evidence is produced:

`Manifest row → implementation reference → test reference → environment → reuse/reference → evidence → status → next action`

When a test fails:
`FAIL → root cause → minimal patch → regression → rerun → evidence update`

When a prerequisite is unavailable:
`OPEN` or `NOT EXECUTED`, never PASS.

This file is the durable handoff point for future chats and must be read before starting the next Manifest-driven execution cycle.
