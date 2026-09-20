# SEPP-MarketRadar v6.0.0 — Operational Completion

This release closes the remaining **implementable Core gaps** between intelligence and operational execution.

## Added
- Provider-neutral authorized API execution with environment-based credentials.
- Idempotent submission keys and immutable operational action log.
- Human-approved guided browser submission preparation.
- Delivery evidence: artifact existence + SHA-256 + immutable evidence record.
- Payment verification record linked to the existing revenue ledger.
- End-to-end operational gate reporting.
- Provider configuration is explicit and disabled by default; no credentials are discovered or bypassed.

## Hard runtime truth
A software package cannot truthfully manufacture external facts. Live source health, third-party account authorization, acceptance, delivery, payment and Windows execution require the corresponding real runtime evidence. v6.0.0 therefore implements the gates and refuses to promote those states without evidence.
