# v6.0.1 — Windows/Runtime Hardening

- Fixed desktop source-policy verification to use a thread-local SQLite connection instead of reusing the Tk UI-thread connection.
- Fixed live source verification state so `LIVE_CONFIRMED` is persisted as runtime `verified`, matching the operational readiness gate.
- Hardened action authorization: evidence IDs must exist, be bound to the target opportunity, and contain usable provenance fields before an authorization can be issued.
- Fixed demand-signal persistence so each matched skill records the actual matched term.
- Added regression coverage for the authorization evidence gate and SQLite/thread boundary.
- Windows build script now uses the Python launcher (`py`) rather than relying on the `python` Store alias.

External Internet/provider credentials, real source health, real account authorization, real delivery/payment, and Windows host execution still require validation in their corresponding real environment.
