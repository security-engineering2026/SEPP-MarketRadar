# SEPP-MarketRadar — Manifest Atomic Requirement Matrix v2.0

**Status:** NORMATIVE EXECUTION REGISTER  
**Manifest:** `docs/MANIFEST.md` v1.0  
**Baseline:** v16.1.2  
**Purpose:** شکستن هر الزام Manifest به واحدهای کوچک قابل پیاده‌سازی، تست و اثبات.

> این سند جایگزین Manifest نیست. Manifest قرارداد است؛ این سند رجیستر اجرای قرارداد است.

## 1. قانون وضعیت

هر Requirement اتمیک باید **سه وضعیت جداگانه** داشته باشد:

- **CODE:** وضعیت پیاده‌سازی کد
- **TEST:** وضعیت تست
- **EVIDENCE:** وضعیت اثبات در محیط صحیح

و یک **GAP TYPE** مشخص می‌کند مشکل دقیقاً از کجاست:

| GAP TYPE | معنی |
|---|---|
| NONE | برای این واحد نقص شناخته‌شده وجود ندارد |
| CODE_MISSING | کد/قابلیت لازم وجود ندارد |
| CODE_INCOMPLETE | کد وجود دارد ولی بخشی از contract ناقص است |
| TEST_MISSING | کد هست ولی regression/negative/adversarial test کافی نیست |
| TEST_FAIL | تست اجرا شده و fail شده |
| ENV_NOT_EXECUTED | تست باید در محیط دیگری اجرا شود ولی هنوز اجرا نشده |
| EVIDENCE_MISSING | تست/کد ممکن است درست باشد ولی evidence لازم ثبت نشده |
| EXTERNAL_CONFIG_MISSING | endpoint/credential/provider/sandbox لازم موجود نیست |
| EXTERNAL_POLICY_MISSING | منبع سیاست/Terms/KYC/Payment لازم هنوز qualification نشده |
| LEGACY_CONFLICT | مسیر قدیمی با Manifest متناقض هنوز فعال است |
| ENVIRONMENT_FAILURE | مشکل runner/network/permission/toolchain مانع اثبات شده |
| UNKNOWN | هنوز اطلاعات کافی برای تعیین نقص نداریم |

**PASS فقط وقتی مجاز است که CODE + TEST + EVIDENCE برای همان واحد تکمیل باشد.**

---

## 2. اولویت

- **P0:** مانع truth/security/core execution/product qualification
- **P1:** قابلیت لازم برای Manifest-conformant product
- **P2:** intelligence/learning/depth
- **P3:** optimization/hardening بعد از contract

---

## 3. Atomic Requirement Matrix

### A. Mission / Truth / Domain

| ID | Requirement اتمیک | محل/مسئولیت کد | تست لازم | CODE | TEST | EVIDENCE | GAP TYPE | راه‌حل موجود؟ | رجوع بیرونی؟ | محیط | Priority | خروجی دقیق |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M-001 | pipeline باید observation تا learning را مدل کند | operationalization / outcome / learning | end-to-end behavioral chain | PARTIAL | PARTIAL | OPEN | EVIDENCE_MISSING | YES | NO | Windows + CI | P0 | زنجیره کامل قابل replay |
| M-002 | evidence از truth جدا باشد | evidence/claim/domain models | negative state tests | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | evidence هرگز truth تلقی نشود |
| M-003 | UNKNOWN یک state معتبر باشد | policy/eligibility/KYC/source state | UNKNOWN propagation tests | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | UNKNOWN به ALLOW تبدیل نشود |
| M-004 | observation مستقل از claim باشد | observation/claim persistence | mutation/provenance tests | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | observation قابل بازسازی |
| M-005 | decision snapshot قابل بازسازی باشد | decision_traces | replay test | PRESENT | PRESENT | PASS | NONE | YES | NO | Windows CI | P0 | decision deterministic/replayable |
| M-006 | outcome از payment جدا باشد | outcome/payment | negative transition tests | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI + sandbox | P0 | delivery ≠ payment |

### B. Domain Contract

| ID | Requirement اتمیک | کد موردنیاز | تست | CODE | TEST | EVIDENCE | GAP TYPE | راه‌حل | بیرونی | محیط | Priority | خروجی |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D-001 | Source identity | source registry model | uniqueness/reload | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | source شناسه پایدار |
| D-002 | Endpoint identity | endpoint model/fields | duplicate endpoint | PRESENT | PARTIAL | OPEN | TEST_MISSING | TEST | NO | CI | P0 | endpoint قابل تشخیص |
| D-003 | Observation identity | observation model | idempotency | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | NO | CI | P0 | observation تکراری ایجاد نشود |
| D-004 | Evidence identity/hash | evidence/raw snapshot | hash/replay/tamper | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | evidence digest پایدار |
| D-005 | Claim identity | claim/conflict layer | conflict/provenance | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | claim قابل ردیابی |
| D-006 | Entity identity | entity resolution | merge/nonmerge | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | NO | CI | P1 | identity محافظه‌کارانه |
| D-007 | Party role | party model | role separation | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI + live | P1 | roleها مخلوط نشوند |
| D-008 | Opportunity identity | canonical opportunity | dedup/reconstruction | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | opportunity stable identity |
| D-009 | Decision identity | decision trace | immutable replay | PRESENT | PRESENT | PASS | NONE | YES | NO | CI | P0 | decision trace |
| D-010 | Action identity | authorization/action | nonce/idempotency | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI + Windows | P0 | action یک‌بار/صحیح |
| D-011 | Outcome identity | outcome ledger | immutability | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P1 | outcome immutable |
| D-012 | Financial observation | payment/revenue models | duplicate/ref verification | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | sandbox | P0 | financial state evidence-bound |

### C. Source Registry / Adapter / Verification

| ID | Requirement اتمیک | کد موردنیاز | تست | CODE | TEST | EVIDENCE | GAP TYPE | راه‌حل | بیرونی | محیط | Priority | خروجی |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S-001 | registry candidate state | sources registry | lifecycle test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI + live | P0 | candidate |
| S-002 | registered ≠ verified | source audit | count separation | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | truthful counts |
| S-003 | source adapter schema | federation adapter contract | contract completeness | PARTIAL | PARTIAL | OPEN | CODE_INCOMPLETE | YES | YES | CI | P0 | every adapter declared |
| S-004 | acquisition method declaration | adapter metadata | metadata audit | PARTIAL | PARTIAL | OPEN | CODE_INCOMPLETE | YES | YES | CI | P0 | method explicit |
| S-005 | endpoint declaration | adapter | endpoint audit | PARTIAL | PARTIAL | OPEN | CODE_INCOMPLETE | YES | YES | CI | P0 | endpoint explicit |
| S-006 | input/output contract | adapter/parser | fixture contract | PARTIAL | PARTIAL | OPEN | CODE_INCOMPLETE | YES | YES | CI | P0 | schema-bound adapter |
| S-007 | access scope/auth declaration | adapter | auth boundary test | PARTIAL | PARTIAL | OPEN | CODE_INCOMPLETE | YES | YES | CI | P0 | scope explicit |
| S-008 | rate/size/timeout declaration | acquisition | limit tests | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P0 | bounded acquisition |
| S-009 | failure semantics | federation/fallback | failure taxonomy | PRESENT | PRESENT | PASS | NONE | YES | NO | Windows CI | P0 | SOURCE_UNAVAILABLE vs provider failure |
| S-010 | verification evidence | verifier | evidence persistence | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | Windows live | P0 | verification reproducible |
| S-011 | stale/revalidation | source verification | expiry/revalidate | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | YES | Windows live | P0 | time-bounded truth |
| S-012 | capability ladder | capability state | promotion/anti-downgrade | PRESENT | PRESENT | PASS | NONE | YES | NO | Windows CI | P0 | monotonic maturity |
| S-013 | 500 live reachability | source verification engine | 500-source gate | PRESENT | NOT EXECUTED/PREVIOUSLY BELOW TARGET | OPEN | ENV_NOT_EXECUTED | YES | YES | Windows live | P0 | ≥500 LIVE_CONFIRMED |
| S-014 | live acquisition sample | federation | real observations | PRESENT | NOT EXECUTED | OPEN | ENV_NOT_EXECUTED | YES | YES | Windows live | P0 | real observation |
| S-015 | social source surface | source family gate | live family sample | PRESENT | NOT EXECUTED | OPEN | ENV_NOT_EXECUTED | YES | YES | Windows live | P1 | social/community surface |
| S-016 | procurement source surface | source family gate | live family sample | PRESENT | NOT EXECUTED | OPEN | ENV_NOT_EXECUTED | YES | YES | Windows live | P1 | procurement surface |
| S-017 | dynamic JS | Playwright gate | browser E2E | PRESENT | NOT EXECUTED | OPEN | ENV_NOT_EXECUTED | YES | YES | Windows live | P1 | rendered source acquisition |

### D. Acquisition / Evidence / Observation

| ID | Requirement | Code | Test | CODE | TEST | EVIDENCE | GAP TYPE | Solution | External | Environment | P | Output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A-001 | host-bound acquisition | federation | cross-host redirect block | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | NO | CI + live | P0 | no SSRF redirect escape |
| A-002 | private-IP protection | federation/network guard | RFC1918/loopback tests | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P0 | private targets blocked |
| A-003 | size bound | acquisition | oversized response | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | memory bounded |
| A-004 | timeout bound | acquisition | slow endpoint | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | timeout deterministic |
| A-005 | retry bound | acquisition | transient failure | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | YES | CI | P0 | bounded retry |
| A-006 | secret isolation | auth headers | redirect/leak test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P0 | secrets never cross boundary |
| A-007 | immutable raw payload | raw snapshot | hash/tamper/replay | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | original payload preserved |
| A-008 | snapshot source binding | snapshot | source mismatch | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | source-bound snapshot |
| A-009 | observation metadata | observation | metadata integrity | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | URL/time/http/content metadata |
| A-010 | provenance retention | observation→opportunity | graph traversal | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | every object traceable |

### E. Canonicalization / Dedup / Entity / Evidence Graph

| ID | Requirement | Code | Test | CODE | TEST | EVIDENCE | GAP TYPE | Solution | External | Environment | P | Output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C-001 | normalize source observations | canonical pipeline | normalization fixtures | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | canonical opportunity |
| C-002 | retain contradictory observations | claim_conflicts | contradiction test | PRESENT | PRESENT | PASS | NONE | YES | NO | CI | P0 | no destructive overwrite |
| C-003 | stable opportunity ID | opportunity identity | repeat observation | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | same opportunity identity |
| C-004 | dedup without title-only replacement | dedup logic | near duplicate fixtures | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P1 | safe dedup |
| C-005 | MATCH/POSSIBLE_MATCH/NO_MATCH | entity resolver | threshold tests | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | NO | CI | P1 | reversible resolution |
| C-006 | party temporal role | party resolution | role/time tests | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI + live | P1 | role history |
| C-007 | evidence graph links | evidence/claim graph | orphan/link traversal | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | complete provenance |
| C-008 | claim-level provenance | claims | missing evidence rejection | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | consequential claims traceable |
| C-009 | trust ≠ evidence confidence | trust | separation tests | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P1 | trust separate |
| C-010 | UNKNOWN trust | trust model | insufficient-evidence tests | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P1 | no forced trust value |

### F. Eligibility / Payment / KYC / Policy

| ID | Requirement | Code | Test | CODE | TEST | EVIDENCE | GAP TYPE | Solution | External | Environment | P | Output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P-001 | eligibility independent | eligibility engine | payment/ranking independence | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI + live | P0 | independent state |
| P-002 | ALLOW | policy/eligibility | positive fixture | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P0 | explicit allow |
| P-003 | REVIEW | policy/eligibility | ambiguity fixture | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P0 | review |
| P-004 | BLOCK | policy/eligibility | hard-block fixture | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P0 | block |
| P-005 | UNKNOWN | policy/eligibility | unknown propagation | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P0 | unknown |
| P-006 | policy version | policy | version reproducibility | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | NO | CI | P0 | versioned decision |
| P-007 | payment detection | payment intelligence | claim detection | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P0 | detected ≠ verified |
| P-008 | payment verification | payment adapter | sandbox verification | PRESENT | NOT EXECUTED | OPEN | EXTERNAL_CONFIG_MISSING | YES | YES | sandbox | P0 | verified payment |
| P-009 | PAID transition | revenue | only verified payment | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI+sandbox | P0 | PAID only after proof |
| P-010 | KYC documented | KYC intelligence | documented-vs-observed | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI + live | P0 | KYC requirement |
| P-011 | KYC UNKNOWN | KYC | unknown negative test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P0 | UNKNOWN/REVIEW |
| P-012 | policy fail closed | policy | contradictory/absent evidence | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | no unsafe execution |

### G. Intelligence / Ranking / Decision

| ID | Requirement | Code | Test | CODE | TEST | EVIDENCE | GAP TYPE | Solution | External | Environment | P | Output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| I-001 | classification | intelligence | fixture classification | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P1 | normalized class |
| I-002 | summarization | intelligence | output contract | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P1 | evidence-bound summary |
| I-003 | demand signal | intelligence | reproducibility | PARTIAL | PARTIAL | OPEN | CODE_INCOMPLETE | YES | YES | CI | P2 | demand metric |
| I-004 | competition signal | intelligence | reproducibility | PARTIAL | PARTIAL | OPEN | CODE_INCOMPLETE | YES | YES | CI | P2 | competition metric |
| I-005 | TTM/market signal | intelligence | temporal fixtures | PARTIAL | PARTIAL | OPEN | CODE_INCOMPLETE | YES | YES | CI | P2 | time-to-market signal |
| I-006 | intelligence cannot authorize | policy/action boundary | adversarial test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | AI/heuristic never authority |
| I-007 | ranking separate from policy | ranking/policy | block override test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | ranking cannot override |
| I-008 | ranking factors exposed | ranking trace | trace test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P1 | explainable ranking |
| I-009 | Top 7 | daily center | exact count test | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | NO | CI + Windows | P1 | exactly 7 |
| I-010 | Do-Now 3 | daily center | exact count/actionability | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | NO | CI + Windows | P1 | exactly 3 |

### H. Approval / Authorization / Action

| ID | Requirement | Code | Test | CODE | TEST | EVIDENCE | GAP TYPE | Solution | External | Environment | P | Output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X-001 | explicit approval | approval broker | approval-required test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | no approval → no action |
| X-002 | target binding | authorization | mismatch test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | target exact |
| X-003 | action binding | authorization | action mismatch | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | action exact |
| X-004 | params digest | authorization | params mutation | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | params exact |
| X-005 | evidence digest | authorization | evidence mutation | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | evidence exact |
| X-006 | policy version binding | authorization | policy version mutation | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | policy exact |
| X-007 | expiry | authorization | expired token | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | expiry fail |
| X-008 | one-time nonce | authorization | replay test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | replay blocked |
| X-009 | idempotent action | action executor | repeated execution | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI+sandbox | P0 | no duplicate side effect |
| X-010 | external reference | action result | reference persistence | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | sandbox | P1 | external result trace |
| X-011 | lifecycle valid transitions | application state machine | all invalid transitions | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | invalid transition blocked |
| X-012 | human approval audit | approval ledger | actor/time/reason | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | auditable approval |

### I. Application / Delivery / Revenue / Learning

| ID | Requirement | Code | Test | CODE | TEST | EVIDENCE | GAP TYPE | Solution | External | Environment | P | Output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L-001 | application lifecycle | application workflow | transition matrix | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI+sandbox | P0 | lifecycle valid |
| L-002 | negotiation state | application | valid/invalid transition | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P1 | negotiation tracked |
| L-003 | acceptance state | application | transition test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P1 | acceptance tracked |
| L-004 | delivery evidence | delivery/artifacts | digest/tamper | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI+sandbox | P1 | delivery proof |
| L-005 | delivery ≠ payment | delivery/payment | negative test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | no false PAID |
| L-006 | revenue separation | revenue ledger | settlement/ref tests | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | sandbox | P0 | revenue auditable |
| L-007 | duplicate payment rejection | payment | duplicate ref | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | sandbox | P0 | duplicate blocked |
| L-008 | outcome immutable | outcome ledger | mutation test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P1 | immutable outcome |
| L-009 | rejection first class | outcome/policy | rejection reason propagation | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P1 | negative evidence retained |
| L-010 | failure first class | recovery/outcome | failure reason test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P1 | failure reusable |
| L-011 | market learning | learning | historical replay | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P2 | additive learning |
| L-012 | learning cannot rewrite observations | learning/raw | immutability test | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | history preserved |

### J. Runtime / Security / Audit / Integrity

| ID | Requirement | Code | Test | CODE | TEST | EVIDENCE | GAP TYPE | Solution | External | Environment | P | Output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R-001 | durable scheduler | scheduler/runtime | restart/resume | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | Windows | P0 | resumable job |
| R-002 | bounded retry | runtime | retry count | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | YES | CI | P0 | bounded retry |
| R-003 | stale handling | runtime/source | stale transition | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | Windows | P0 | stale explicit |
| R-004 | recovery | recovery | kill/restart/recover | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | Windows | P0 | recoverable state |
| R-005 | SSRF private IP | network guard | adversarial URLs | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P0 | private IP blocked |
| R-006 | redirect boundary | federation | cross-host redirect | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | NO | CI + live | P0 | host boundary |
| R-007 | secret isolation | auth | redirect/header leak | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | CI | P0 | no secret leakage |
| R-008 | replay detection | authorization | nonce reuse | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | replay blocked |
| R-009 | immutable audit | audit DB | UPDATE/DELETE tamper | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | audit immutable |
| R-010 | parser isolation | parser | network-disabled parser | PARTIAL | PARTIAL | OPEN | CODE_INCOMPLETE | YES | YES | CI | P0 | parser cannot network |
| R-011 | least privilege | runner/service | permission boundary | PARTIAL | NOT EXECUTED | OPEN | ENV_NOT_EXECUTED | YES | YES | Windows | P0 | least privilege proven |
| R-012 | DB FK/unique | DB schema | constraint violation | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | NO | CI | P0 | invalid state rejected |
| R-013 | transaction rollback | DB | forced exception | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | atomic transaction |
| R-014 | idempotency keys | execution | duplicate request | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | no duplicate |

### K. Windows / Android / UI / Reporting

| ID | Requirement | Code | Test | CODE | TEST | EVIDENCE | GAP TYPE | Solution | External | Environment | P | Output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W-001 | portable EXE | packaging/build_windows.ps1 | real build | PRESENT | PRESENT | OPEN | ENV_NOT_EXECUTED | YES | YES | Windows runner | P0 | EXE artifact |
| W-002 | EXE smoke | EXE | --smoke-test | PRESENT | PRESENT | OPEN | ENV_NOT_EXECUTED | YES | NO | Windows | P0 | process exits 0 |
| W-003 | UI smoke | desktop/UI | --ui-smoke-test | PRESENT | PRESENT | OPEN | ENV_NOT_EXECUTED | YES | YES | Windows | P0 | UI starts/closes |
| W-004 | installer build | installer | Inno build | PRESENT | PRESENT | OPEN | ENV_NOT_EXECUTED | YES | YES | Windows | P0 | installer artifact |
| W-005 | clean install | installer | silent install | PRESENT | PRESENT | OPEN | ENV_NOT_EXECUTED | YES | NO | Windows | P0 | clean install |
| W-006 | installed EXE | installer | launch installed binary | PRESENT | PRESENT | OPEN | ENV_NOT_EXECUTED | YES | NO | Windows | P0 | installed product runs |
| W-007 | uninstall | installer | silent uninstall + cleanup | PRESENT | PRESENT | OPEN | ENV_NOT_EXECUTED | YES | NO | Windows | P0 | removal clean |
| W-008 | first-run acquisition | desktop bootstrap | fresh DB trigger | PRESENT | PRESENT | OPEN | ENV_NOT_EXECUTED | YES | NO | Windows live | P0 | fresh install starts acquisition |
| W-009 | Windows service/filesystem | runtime | service/ACL/filesystem smoke | PARTIAL | NOT EXECUTED | OPEN | ENV_NOT_EXECUTED | YES | YES | Windows | P0 | runtime permission contract |
| W-010 | Android authority boundary | Android gateway | reject local policy/payment authority | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | Android emulator | P1 | Windows remains authority |
| W-011 | Android E2E | Android | emulator qualification | PRESENT | PRESENT | PASS | NONE | YES | YES | Linux emulator | P1 | companion E2E |
| W-012 | UI truth states | UI | UNKNOWN/REVIEW/BLOCKED visual+semantic | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | YES | Windows UI | P0 | truthfully displayed state |
| W-013 | observability status taxonomy | observability/UI | attempted/success/fail/skip/unknown | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI + Windows | P1 | status truthful |
| W-014 | reporting counts | reports/audit | DB/report reconciliation | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | registry≠verified counts |
| W-015 | audit exposure | audit/report | missing-evidence visibility | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | OPEN gaps visible |

### L. Governance / Definition of Done

| ID | Requirement | Code/process | Test | CODE | TEST | EVIDENCE | GAP TYPE | Solution | External | Environment | P | Output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G-001 | every feature maps to Manifest | process | manifest alignment test | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | NO | CI | P0 | no unmapped feature |
| G-002 | AS-IS audit before implementation | process/docs | audit presence check | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | gap known before coding |
| G-003 | solution search before rebuild | process | review/audit evidence | PRESENT | PARTIAL | OPEN | EVIDENCE_MISSING | YES | NO | CI | P0 | reuse considered |
| G-004 | regression after patch | process | CI gate | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | NO | CI | P0 | patch proven |
| G-005 | environment-specific evidence | process | evidence matrix | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | correct environment |
| G-006 | legacy contradictions retired | code/audit | contradiction scan | PARTIAL | PARTIAL | OPEN | LEGACY_CONFLICT | YES | NO | CI | P0 | old path removed/disabled |
| G-007 | audit update after test | process | audit diff check | PRESENT | PARTIAL | OPEN | TEST_MISSING | YES | NO | CI | P0 | status current |
| G-008 | Manifest terminology locked | docs/process | manifest alignment | PRESENT | PRESENT | OPEN | EVIDENCE_MISSING | YES | NO | CI | P0 | no silent contract drift |
| G-009 | final architecture boundaries | architecture | end-to-end replay | PARTIAL | PARTIAL | OPEN | CODE_INCOMPLETE | YES | NO | Windows + CI | P0 | WORLD→OBS→EVIDENCE→STATE→DECISION→ACTION→OUTCOME→LEARNING |

## 4. Exact classification rule for every OPEN/FAIL

برای هر ردیف که PASS نیست، **قبل از هر coding** باید یکی از این تشخیص‌ها ثبت شود:

1. **CODE_MISSING** — اصلاً implementation ندارد.
2. **CODE_INCOMPLETE** — implementation دارد اما contract ناقص است.
3. **TEST_MISSING** — implementation کافی است ولی test ندارد.
4. **TEST_FAIL** — test اجرا شده و واقعاً fail شده.
5. **ENV_NOT_EXECUTED** — test آماده است ولی محیط authoritative هنوز اجرا نشده.
6. **EVIDENCE_MISSING** — test pass شده ولی evidence/audit کافی ثبت نشده.
7. **EXTERNAL_CONFIG_MISSING** — endpoint/credential/sandbox لازم وجود ندارد.
8. **EXTERNAL_POLICY_MISSING** — policy/terms/KYC/payment reference لازم qualification نشده.
9. **LEGACY_CONFLICT** — implementation جدید با مسیر قدیمی متناقض است.
10. **ENVIRONMENT_FAILURE** — runner/toolchain/permission/network مانع اجرا شده است.

هیچ‌کدام نباید با «کد ناقص» یا «تست پاس نشده» قاطی شوند.

## 5. External / internal solution search contract

برای هر GAP غیر-PASS، ترتیب اجباری جستجو:

`Same Repo → CDR Core → Software_Forge → Git History → Mature OSS → Official Library/Docs`

ستون **راه‌حل موجود؟** فقط زمانی YES است که یک implementation/pattern/test قابل استفاده واقعاً پیدا شده باشد.

ستون **رجوع بیرونی؟** باید مشخص کند:
- NO = هنوز external search لازم نشده؛
- YES = منبع بررسی شده؛
- REQUIRED = برای بسته‌شدن این requirement باید provider/official documentation بررسی شود.

صرف اینکه «کتابخانه‌ای وجود دارد» به معنی حل شدن requirement نیست.

## 6. Authoritative environment matrix

| Environment | فقط برای چه چیزی authoritative است |
|---|---|
| GitHub-hosted CI | unit/regression/domain/contract/security tests |
| Self-hosted Windows | EXE/installer/UI/service/filesystem/live network/source scale |
| Android Linux emulator | Android build/E2E/authority boundary |
| External sandbox | engine/application/payment/notification contracts |
| Live provider/network | source reachability/policy/terms/provider behavior |

## 7. Current P0 execution order

1. W-001…W-009 — Windows product evidence
2. R-005…R-014 — security/integrity boundaries
3. S-013/S-014 — 500-source + live acquisition
4. P-001…P-012 — eligibility/KYC/payment/policy
5. X-001…X-012 — approval/authorization/action
6. L-001…L-012 — application/delivery/payment/outcome
7. G-001…G-009 — governance enforcement
8. P1/P2 intelligence, social/procurement, learning depth

## 8. Locked execution behavior

هر cycle:

`READ MATRIX → PICK HIGHEST PRIORITY GAP → AS-IS CODE → SEARCH EXISTING SOLUTION → PATCH → ATOMIC TEST → REQUIRED ENVIRONMENT → CI → UPDATE THIS MATRIX`

**Broad suite is not a substitute for atomic proof.**

اگر یک ردیف CODE_INCOMPLETE باشد، قبل از اجرای qualification بزرگ باید همان نقص کد مشخص و اصلاح شود.

اگر CODE=PASS و TEST=MISSING باشد، کدنویسی مجدد ممنوع است؛ باید test اضافه شود.

اگر TEST=PASS و EVIDENCE=OPEN باشد، کد دستکاری نمی‌شود؛ فقط evidence محیط صحیح اجرا/ثبت می‌شود.

اگر ENVIRONMENT_FAILURE باشد، defect محصول فرض نمی‌شود تا root cause اثبات شود.

## 9. Baseline rule

این ماتریس با هر تغییر Manifest، code contract، test contract یا qualification gate باید version/update شود.

**Merge این سند به main بدون دستور صریح کاربر ممنوع است.**
