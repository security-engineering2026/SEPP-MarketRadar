# v6.0.4 — Windows Reliability & Release Integrity

- Fixed remaining Windows SQLite test cleanup paths so file-backed databases are explicitly closed before temporary directories are removed.
- Fixed temporary database hygiene in desktop/federation regression tests.
- Closed the one-time authorization TOCTOU race by atomically claiming an authorization before external execution.
- Tightened source-audit `promotable` semantics: schema-valid or merely listed sources are not advertised as promotable unless they are live-confirmed, verified, warning-free, and not blocked.
- Bumped all current product/version metadata to 6.0.4 / Android versionCode 6040.
- Regenerated release verification artifacts.

- Policy verification hardening: search-engine snippets are discovery hints only and are no longer treated as authoritative Iran/KYC/payment evidence.
- Release hygiene: final package excludes pytest/bytecode/runtime caches.
