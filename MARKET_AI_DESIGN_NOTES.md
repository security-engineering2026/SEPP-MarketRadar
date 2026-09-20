# Market AI Design Notes — v4.16.0

## Principle
LLMs assist discovery, extraction, clustering, summarization and recommendation. They do **not** decide source eligibility, sanctions restrictions, KYC status or execution authorization by themselves.

## Current market patterns used as design input
- OpenAI: current API catalog emphasizes frontier reasoning/coding, tool use, web/file search and computer use. Use a strong model for deep source adjudication and a cheaper model for high-volume extraction.
- Anthropic: current Claude lineup emphasizes adaptive thinking, long-context work and agentic systems. Use a high-reasoning tier for difficult evidence synthesis and a fast tier for routine classification.
- Google Gemini: current 3.x line emphasizes coding/agents, high-volume Flash variants and computer-use capabilities. Use Flash-class models for high-volume source triage where policy rules remain deterministic.
- Mistral: current lineup includes agentic/coding-oriented Medium, efficient Small and OCR models. Use small/efficient models for structured extraction and OCR when source evidence arrives as documents/images.

## Proposed router

```text
Source Discovery
      |
      +--> Fast Extractor
      |
      +--> Duplicate / Cluster
      |
      +--> Evidence Summarizer
      |
      +--> Deep Reviewer (only ambiguous/high-value cases)
      |
      v
Deterministic Policy Engine
      |
      +--> ALLOW / BLOCK / UNKNOWN
      |
      v
Action Center
```

## Model lifecycle rule
Model IDs are configuration, not hard-coded business logic. Every provider adapter records model ID, timestamp, task, evidence hashes and confidence. A model can be replaced without changing policy logic.

## Never delegate to an LLM
- Sanctions / Iran source eligibility final decision
- KYC `NOT_REQUIRED` final proof
- Payment verification
- Authorized submission approval
- Credential handling
- CAPTCHA/2FA/KYC bypass decisions
