# 30 · Résumé Project Bullets

> **Internal preparation note — not project documentation.**
> Working material for writing a résumé entry. Not referenced from the README.
> Every number below is verified in `28_Project_Fact_Sheet.md`. Pick the numbers
> most relevant to the role being targeted — do not use all of them at once.

---

## Shared skeleton

**BuildHealth — Existing Building Health Monitoring & Intelligent Retrofit
Decision Platform** · prototype, solo project

> One-line framing that works for all three versions:
> *"Digitised a building condition-assessment workflow — monitoring data through
> anomaly detection, health scoring, risk classification and retrofit
> prioritisation — with every result traceable to its source data."*

---

## Version A · TIC / Inspection / Engineering Technical Services

For roles where the emphasis is inspection methodology, condition assessment,
and defensible findings.

- Designed a condition-assessment workflow that turns continuous monitoring data
  into three parallel anomaly detections — absolute threshold, rate of change,
  and statistical z-score — because no single method captures both sudden
  excursions and gradual deterioration.
- Built a 0–100 Building Health Index over five weighted dimensions, with
  dimension inputs validated rather than silently clamped, so bad data surfaces
  instead of producing a plausible-looking score.
- Implemented a four-tier risk classification with a conservative override rule:
  any HIGH-severity anomaly forces a minimum tier, erring toward over-alerting
  rather than under-reporting.
- Made every result traceable — each recommendation resolves back through its
  triggering anomalies to the specific sensor and readings, with the calculation
  version recorded at every layer.

## Version B · Engineering Consulting / Project Management

For roles where the emphasis is prioritisation, decision support, and
communicating engineering judgement.

- Built a retrofit prioritisation model that scores candidate actions 0–100 from
  five weighted sub-scores (risk severity, trend, component importance, urgency,
  cost efficiency) and ranks them, so limited budget can be directed
  defensibly.
- Paired the priority model with a rule engine that produces categorised
  recommendations with cost level and urgency, converting analysis output into
  an actionable shortlist rather than a single opaque score.
- Designed the platform around an explicit evidence chain — recommendation →
  anomaly → sensor → reading — so any prioritisation can be justified to a
  reviewer.
- Completed the project with **412 backend tests** and **97 frontend tests**
  passing, including tests that pin engineering parameters against the engine's
  actual behaviour so the displayed values cannot silently drift from the
  computed ones.

## Version C · Digital Engineering / Data / AI

For roles where the emphasis is software, data pipelines, and applied AI.

- Implemented an end-to-end engineering data pipeline in Python/FastAPI —
  SQLAlchemy data model, analytics engine, service layer, 19 REST endpoints —
  with the analytics layer decoupled from the API so the computation is
  independently testable.
- Diagnosed and fixed an N+1 access pattern by measuring query counts: the same
  monitoring series was read three times per building. Batching reduced the
  dashboard from 28 to 7 queries and the retrofit overview from 64 to 6, with
  query count no longer scaling with building count.
- Profiled further, found the bottleneck had moved from database to CPU
  (anomaly detection was ~92% of response time), and introduced a
  request-scoped analysis object that eliminated a duplicate computation —
  cutting the AI context path from 59.0 ms to 31.5 ms (**−47%**, local
  benchmark).
- Added RAG grounding over an internal knowledge base using a standard-library
  TF-IDF retriever (no vector database), and enforced a runtime safety layer:
  43 forbidden phrases scanned on every response, server-side disclaimer,
  retrieved citations forced from the retriever, and engineering evidence kept
  structurally separate from knowledge evidence.

---

## What not to write

- Do not claim real-world deployment, real building data, or real users.
- Do not claim structural appraisal, certification, collapse prediction, or
  automatic design capability.
- Do not describe the performance numbers as production benchmarks — they are
  local development measurements (8 GB M2 Air, SQLite, 3 buildings, 1350
  records, median of 5 runs).
- Do not present the parameters as standards — they are prototype values.
- Do not describe the AI as performing engineering computation. It explains
  results that deterministic algorithms produced.

## Optional numbers, by relevance

| Number | Best used for |
|---|---|
| 28 → 7 queries (dashboard) · 64 → 6 (retrofit overview) | Data / backend roles |
| 59.0 → 31.5 ms, −47% (AI context path) | Performance-sensitive roles |
| 412 backend · 97 frontend tests · 19/19 API smoke | Quality-focused framing |
| 3 detection methods · 5 BHI dimensions · 4 risk tiers | TIC / inspection framing |
| 5 weight sub-scores · evidence chain | Consulting / prioritisation framing |
| 43 redlines · 5 knowledge documents · 23 chunks | AI safety / RAG framing |
