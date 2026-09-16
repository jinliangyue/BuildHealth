<!--
title: BuildHealth Engineering Knowledge Base
purpose: This knowledge base provides project-internal engineering notes used by Phase 6B RAG.
source: BuildHealth Internal Engineering Notes
-->

# BuildHealth Engineering Knowledge Base

> **BuildHealth Internal Engineering Notes** · Phase 6B
> RAG knowledge base for the AI Engineering Assistant

## Purpose

This directory contains project-internal engineering documentation that the
AI Engineering Assistant can reference when explaining a building's status
to a human user. The retrieval mechanism is **lexical** (TF-IDF + cosine
similarity, Python standard library only). No vector database, no embedding
service, no internet crawl.

## Source

Every document here is hand-written from the BuildHealth codebase.
All quantitative thresholds (e.g. BHI dimension weights, risk-classification
boundaries, RAG top-k) are maintained in source code under
`backend/app/analytics/config.py` and `backend/app/knowledge/retriever.py`.
This knowledge base contains only **conceptual explanations**; the numbers
live in code.

## Limitations

These documents are **NOT**:
- National standards (no Chinese national standard codes, no ISO codes).
- Industry codes (no ACI-series, no European structural codes, no AISC codes).
- Professional engineering appraisal or building safety certification.
- Legal compliance material.
- Substitute for code review of `backend/app/`.

If a fact is not present here **and** not present in `backend/app/`, then
the AI must say "current data insufficient" rather than infer.

## Document Map

| File | Topic | Used When Asking About |
|---|---|---|
| `anomaly_detection.md` | Threshold / rate-of-change / zscore | "Why was this anomaly flagged?" |
| `health_assessment.md` | BHI, 5 dimensions, weights | "How is BHI computed?" |
| `risk_classification.md` | 4-tier risk, override rule | "Why is this building HighRisk?" |
| `retrofit_decision.md` | RP-v1.0 priority formula | "Why is this retrofit recommended?" |
| `engineering_redlines.md` | 10 redlines, mandatory disclaimer | "Why does the system refuse to say X?" |

## Engineering Data ≠ Knowledge

`docs/` (and the live `data/buildhealth.db` rows) describe the **specific
buildings currently monitored**. `knowledge/` describes **general engineering
concepts**. The two must never be conflated: a knowledge document does
**not** prove that a condition exists in the current building. Only
sensor data, anomaly history, BHI, risk classification, and retrofit
recommendations do that. Knowledge is **background**, not **evidence**.

## Disclaimer

All content here is **Prototype Design Parameters**, **not** a national
or industry standard. They do not constitute professional engineering
appraisal, structural design, or a building safety certification.
Qualified professional review is required for any actionable decision.
