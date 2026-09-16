# BuildHealth

**Existing Building Health Monitoring & Intelligent Retrofit Decision Platform**

*Civil engineering · engineering data · digitalisation · engineering decision support*

---

## 1. One-line description

A digital decision-support platform for monitoring, assessing, and prioritising
retrofit actions for existing buildings.

---

## 2. Engineering problem

Existing building stock is large and ageing, while condition assessment still
depends largely on periodic manual inspection — expensive, slow, and hard to
scale. Monitoring systems can collect continuous data, but raw sensor values are
not a decision basis on their own. Between the sensor and the engineer there is a
missing layer: an explainable, reproducible, clearly bounded engineering
analysis layer.

BuildHealth implements that layer. It is not a chatbot, not a smart-home
project, and not a pure software exercise. The domain problem drove the design.

| Current situation | Gap |
|---|---|
| Ageing existing building stock | Manual inspection is costly and infrequent |
| Monitoring systems collect data continuously | Raw values are not a decision basis |
| Condition judgement relies on experienced engineers | Expertise is hard to capture and scale |
| AI can produce fluent language | It must not perform engineering calculation or issue conclusions |

The design answer: **deterministic engineering algorithms compute; the AI layer
explains.** The two are strictly separated, and the AI layer is constrained by
automated redlines.

---

## 3. System architecture

```
Monitoring data (crack width · tilt · temperature · humidity · electricity)
        │
        ▼
Anomaly Detection        threshold · rate-of-change · z-score (3 methods in parallel)
        │                → deduplicated by severity signature
        ▼
Building Health Index    BHI 0-100, weighted over 5 dimensions
        │
        ▼
Risk Classification      4 tiers + HIGH-anomaly override rule
        │
        ▼
Retrofit Decision        RP-v1.0 priority · REC-v1.0 recommendation rules
        │                → evidence chain back to sensor / anomaly / BHI
        ▼
AI Explanation Layer     reads the computed results only, plus a
                         project-internal knowledge base (RAG)
        │
        ▼
React dashboard          8 pages, every figure traceable to the API
```

Stack layers: SQLite → SQLAlchemy → analytics engine → service layer → FastAPI
→ React/TypeScript. 19 documented HTTP endpoints, 8 tables.

**The governing constraint is one-way data flow.** Every engineering number is
produced by the backend algorithms. The AI cannot modify, invent, or conclude.
The disclaimer on AI output is overwritten server-side with a fixed text, and
`knowledge_evidence` is taken from the retriever — the model's own citations are
discarded.

---

## 4. Anomaly detection

Three methods run in parallel, because each has a different blind spot:

| Method | Catches | Parameters |
|---|---|---|
| Absolute threshold | Sudden excursions | crack width 0.20 / 0.30 mm · tilt 3.0 / 4.0 ‰ · temperature 40 °C · humidity 85 % |
| Rate of change | Developing trends | per-metric absolute delta and relative % thresholds |
| Z-score | Departure from statistical history | 7-day rolling window · \|z\| > 4 anomaly · \|z\| > 6 HIGH · disabled for electricity and humidity (too noisy) |

Detections are deduplicated on `(sensor, metric, method, severity)` within a
configurable window, so one physical event does not produce a burst of
duplicate alerts.

---

## 5. Building Health Index (BHI)

`BHI = Σ (dimension score × weight)`, range [0, 100]:

| Dimension | Weight | Input |
|---|---|---|
| Structural Safety | 0.40 | Structural anomalies (crack, tilt) |
| Facility Condition | 0.20 | Age vs design life |
| Environmental Quality | 0.15 | Temperature and humidity stability |
| Energy Performance | 0.10 | Electricity coefficient of variation |
| Fire Safety | 0.15 | Floor count and age (placeholder) |

Dimension inputs outside [0, 100] raise an error rather than being silently
clamped.

The weights are **Prototype Design Parameters (BHI-v1.0)**. They are engineering
judgement encoded in configuration — not a national or industry standard — and
the platform says so wherever they are displayed.

---

## 6. Risk classification

Four tiers from the BHI: `≥ 90` Normal · `≥ 75` Attention · `≥ 60` Abnormal ·
`< 60` HighRisk.

An override rule applies on top: **any HIGH-severity anomaly forces a minimum of
Attention**, regardless of the composite score. A building can score acceptably
on aggregate while having a serious local defect; the rule errs toward
over-alerting rather than under-alerting.

Classification is a **Prototype Risk Classification (RISK-v1.0)**, explicitly not
a legally binding building safety grade.

---

## 7. Retrofit decision support

Two versioned models, both prototype:

- **RP-v1.0** — retrofit priority, 0-100 from five weighted sub-scores
  (risk severity 0.35, trend 0.25, component importance 0.20, urgency 0.10,
  cost efficiency 0.10). Banded Low / Medium / High / Very High.
- **REC-v1.0** — a rule engine producing retrofit recommendations by category,
  each with a cost level and an urgency.

Recommendations are computed in real time from current data rather than stored.
Output is decision support: it sequences and explains candidate actions. It is
not an automatic structural design.

---

## 8. Evidence chain

Every recommendation can be traced back through:

```
recommendation → triggering anomalies → sensors → monitoring records
               → BHI dimension scores → risk tier
```

The same chain is exposed to the AI layer and rendered in the UI, where evidence
items link back to the page they came from. Traceability is a first-class
requirement, not a debugging aid: an engineering claim that cannot be traced to
data is not a usable claim.

Each layer also carries a calculation version — BHI-v1.0, RISK-v1.0, ANOM-v1.0,
RP-v1.0, REC-v1.0, AI-v1.0 — so a past result can be interpreted against the
parameters that produced it.

---

## 9. AI engineering assistant

An explanation layer over the deterministic results. Two provider modes:

- **Mock (default)** — deterministic, fully offline, no external calls. Used for
  demonstration and for the entire test suite.
- **OpenAI-compatible (optional)** — any OpenAI-compatible endpoint, configured
  by environment variables. No vendor SDK is installed; the call is plain HTTP.

Safety properties, all enforced in code and covered by tests:

- 43 forbidden phrases (of which 11 are RAG-specific), scanned on every response
- the disclaimer is forced server-side; a model's own disclaimer is discarded
- the user question is declared untrusted input in the system prompt
- the knowledge context is declared untrusted and explicitly subordinate to the
  building's engineering data
- schema validation on every field, with bounded truncation
- prompt-injection attempts resolve to a `safety_violation` error rather than a
  plausible-sounding answer

---

## 10. Engineering knowledge RAG

A project-internal knowledge base of 5 hand-written Markdown documents on the
platform's own concepts: anomaly detection, BHI, risk classification, retrofit
decision, and the engineering redlines. 23 chunks after section-based chunking.

Retrieval is **lexical and deterministic**: TF-IDF with cosine similarity,
implemented in the Python standard library. No vector database, no embedding
service, no internet access. Top-3 chunks, relevance score in [0, 1].

Reasons for the lightweight approach: the requirement is offline, reproducible,
and explainable. TF-IDF ranking can be justified numerically from document
frequencies and asserted in tests; embeddings would introduce model downloads,
non-deterministic floating point, and an external service dependency. At this
corpus size a vector index would add infrastructure without adding retrieval
quality.

**Knowledge is not evidence.** The knowledge base provides general background
concepts; the building's measured data provides evidence about that building.
They are separate fields in the response schema, separate keys in the prompt,
and separate sections in the UI. The model is instructed that knowledge context
never overrides engineering data, and the corpus itself is scanned to guarantee
it contains no standard codes and no redline phrases.

---

## 11. Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18 · TypeScript 5 · Vite 5 · Tailwind 3 · ECharts 5 |
| Backend | Python 3.9 · FastAPI · SQLAlchemy 2.0 · Pydantic 2 |
| Database | SQLite (development, single file) |
| Analytics | NumPy / SciPy where the algorithms need them |
| AI | Mock provider (default) · OpenAI-compatible HTTP provider (optional) |
| Retrieval | Python standard library only (TF-IDF + cosine) |
| Testing | pytest + FastAPI TestClient · Vitest + Testing Library |

---

## 12. Testing

| Suite | Result |
|---|---|
| Backend | **401 passed** |
| Frontend | **97 passed** (15 files) |
| TypeScript | 0 errors |
| Production build | passes (714 modules) |
| API smoke test | 19/19 endpoints responding |

Beyond the usual unit and API coverage, the suite pins properties that are easy
to lose silently:

- frontend and backend engineering parameters cannot drift apart — the
  cross-language test compares the frontend constants against the analytics
  engine's *behaviour*, not against copied literals
- aggregate endpoints must not grow their query count with the number of
  buildings
- batched data loading must return exactly what the per-item loading returned
- the AI safety redlines apply to both providers at runtime
- the knowledge corpus contains no standard codes and no forbidden phrases

A single `bash scripts/verify.sh` runs the backend tests, frontend tests, type
check and production build serially.

---

## 13. Safety and scope boundaries

The platform **does not** and will not:

- perform a structural appraisal or issue a safety certification
- predict collapse or structural failure
- generate automatic structural design or reinforcement drawings
- claim compliance with any national or industry standard
- replace a qualified structural engineer or professional inspection

These are not disclaimers bolted on at the end. They are enforced by the redline
list, the forced disclaimer, the schema validation, and the corpus scan — and
each is covered by tests.

---

## 14. Simulated data limitation

All monitoring data is **simulated**, produced by a deterministic time-series
generator with baseline, trend, periodic fluctuation, noise, and event
components. The demonstration dataset is 3 buildings, 15 sensors, 1350
monitoring records, and 187 generated alerts.

No real building, community, or site is monitored. No IoT, MQTT, or hardware
integration exists. The dashboard carries a permanent simulated-data watermark
and a dedicated data-source page.

The simulation exists so the engineering pipeline can be developed, tested, and
demonstrated end to end without needing proprietary building data. Replacing it
with real monitoring data is a matter of adapting the ingestion layer — the
analytics contract is unchanged.

---

## 15. Future roadmap

Not started; listed for direction.

**Engineering**
- serve all frontend parameters from the API (partially done — the parameter
  endpoint exists; the weight constants remain as an offline fallback)
- batch the remaining per-building queries in the retrofit overview
- compute anomaly detection once per request rather than once per aggregate
  (currently ~92% of dashboard response time)
- persist retrofit recommendations instead of recomputing them per request

**Data**
- ingest real monitoring formats (CSV, standard time-series protocols)
- multi-building time-axis alignment and cross-building comparison

**AI**
- retrieval quality: domain vocabulary and synonym expansion
- conversation and context management — deliberately out of scope today

---

## Positioning note

This project was built by a civil engineering student as a digital
decision-support system: domain problem first, engineering analytics second,
AI as an explanation layer over deterministic results. The AI-assisted
development accelerated the implementation, but the architecture — what is
computed, what is explained, and what is refused — comes from the engineering
constraints.
