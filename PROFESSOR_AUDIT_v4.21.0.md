# Professor / Adversarial Audit — v4.21.0

## Verdict

**PASS — architecture is moving toward the intended adaptive opportunity system.**

The v4.20 weakness was that discovery and source intelligence could dominate the product while application and outcome loops remained shallow. v4.21 corrects that imbalance by making opportunity signals, acceptance probability, expected value and outcome learning executable first-class capabilities.

## Evidence

- Full regression suite: PASS.
- UI smoke: PASS.
- Python compilation: PASS.
- Product audit: PASS, 679 registered contracts, 48 active, 0 invalid.
- Release audit: PASS, version 4.21.0, 0 errors.
- Deterministic Judge→Maker audit: PASS, 100/100 passes.

## Adversarial findings and patches

| Attack / failure mode | Result |
|---|---|
| Missing deadline | Safe UNKNOWN; no fabricated deadline |
| Malformed deadline | Safe fallback; confidence retained separately |
| Missing proposal count | Competition falls back to neutral prior |
| Fake/highly optimistic reputation | Score is bounded and confidence-aware |
| Sparse outcome history | Smoothed prior prevents zero-data overconfidence |
| Rejected opportunity | Immutable outcome and reason can feed learning |
| Browser transient failure | Retry/backoff with immutable attempt records |
| Silent automated submission | Not allowed by guided browser path |
| CAPTCHA / 2FA bypass | Not implemented |
| Source-specific adapter mismatch | Registry boundary + generic safe fallback |
| Revenue without delivered state | Existing DB/application guard remains active |
| Paid state without revenue | Existing trigger remains active |
| Evidence mutation | Existing immutable evidence trigger remains active |

## Important honesty boundary

Local extraction/ranking/learning is tested. Live Internet-wide discovery, live marketplace scraping, real browser session recovery and real submission remain environment/provider/authorization dependent. The product does not receive a "live" grade merely because a module exists.
