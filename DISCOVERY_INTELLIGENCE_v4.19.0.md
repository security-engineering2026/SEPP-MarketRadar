# v4.20.0 — Discovery Intelligence

## Search model

MarketRadar no longer models search as one string. Query plans have explicit modes:

- broad
- exact phrase (`"..."`)
- domain constrained (`site:`)
- exclusion (`-term`)
- freshness (`after:` / `before:`)
- forum/community
- policy/eligibility
- hashtag

Google documents exact phrase, `site:` and exclusion operators as supported search syntax. citeturn0search6

## Search federation

The provider layer now supports Brave, Bing, Serper and a SearXNG-compatible local endpoint. SearXNG is useful for Windows laboratory execution because it can run locally and federate multiple search engines; Windows-specific packaging projects also exist.

## Intelligence Graph

```text
Query Plan
  -> Search Result
      -> Community / Policy / Domain / Country signals
      -> Source Candidate
      -> Evidence
      -> Intelligence Node
      -> Intelligence Edge

Historical yield -> Query priority (not policy decision)
Official policy evidence -> deterministic eligibility gate
```

Community discussions are discovery/intelligence signals, not authoritative eligibility proof.

## Live proof boundary

A local test proves planning, parsing, persistence and failure handling. A **Live Discovery** claim additionally requires:

1. configured legal search provider or self-hosted search federation;
2. outbound Internet connectivity;
3. actual provider responses;
4. persisted raw result provenance;
5. source verification after discovery.

The current build was executed in an environment where SearXNG was not running and no paid provider key was configured, so the autonomous run correctly recorded provider/network failures rather than fabricating discovery.

## Windows

The application remains Windows-first for the product release. The discovery architecture is not intrinsically Windows-only: the provider contract can run on any supported Python runtime. Windows is the primary production/lab target.
