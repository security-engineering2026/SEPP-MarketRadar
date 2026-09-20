# SEPP-MarketRadar v15.1.0 — Integrated Release Notes

This package consolidates the 15.0.0 operational baseline, the policy-intelligence patch, and the subsequent architecture changes completed in the working session.

## Core behavior

- **Project Radar:** execution-eligible sources are intended for hourly discovery of new opportunities.
- **Market Intelligence:** foreign/incompatible sources are retained and intended for twice-daily demand/product discovery.
- **Blacklist:** operationally verified Israel-linked sources/opportunities are archived and excluded from recommendations; records are not deleted.
- **Taxonomy:** opportunities are normalized into domain, task, operations, inputs, outputs, requirements and QA.
- **Personalization:** recommendations respect enabled domains, level, course state and stretch policy.
- **Capability/Provider:** Engine connection is optional; absence of a provider never rejects a manually executable project.
- **Productization:** recurring demand can generate an evidence-backed Product Build Spec for a future standalone Engine.

## Local verification

Full pytest, compileall, product audit, release hardening and fresh-database final verification were executed in the Linux integration environment. The package does not claim live-network, Windows installer, or external Engine execution gates that were not executable in this environment.
