# 28 · Project Fact Sheet

> The single source of truth for anything written about BuildHealth elsewhere
> (README, documentation, presentations, summaries). Every statement here is
> checked against the current code and documentation.
>
> Each item is tagged:
> **[implemented]** working code that runs today ·
> **[prototype]** implemented, but the parameters are prototype values ·
> **[simulated]** works on generated data, not real site data ·
> **[limitation]** known and accepted ·
> **[roadmap]** not built.

**Version**：v1.1 · 2026-09-26 (v1.1 release prep)
**Baseline commit**：`ef095b5`

---

## 1. Project name

**BuildHealth**

## 2. English project name

**Existing Building Health Monitoring & Intelligent Retrofit Decision Platform**

## 3. One-line description

An engineering decision-support platform for monitoring, assessing, and
prioritizing retrofit actions for existing buildings.

## 4. Project positioning

**Digital civil engineering · engineering data · engineering decision support ·
AI-assisted explanation**

BuildHealth explores how digital monitoring and data-driven analysis can
support the assessment and prioritization of retrofit actions for existing
buildings.

It is an engineering prototype that makes a condition-management workflow
digital, structured, and traceable:

```
building record → monitoring data → analysis → anomaly detection
→ health assessment → risk classification → retrofit decision
→ AI-assisted explanation
```

It is not a structural appraisal tool, not a certification system, and not an
autonomous engineering system. **[prototype]**

## 5. Engineering problem

| Situation | Gap |
|---|---|
| Existing building stock is large and ageing | Condition assessment relies mainly on periodic manual inspection — costly, slow, difficult to scale |
| Monitoring systems can collect data continuously | Raw sensor values are not, by themselves, a decision basis |
| Condition judgement depends on experienced engineers | Expertise is difficult to capture and transfer |
| Software can present data | A dashboard alone does not produce a defensible engineering conclusion |

The gap BuildHealth addresses is the analysis layer between a sensor reading and
an engineering decision: something explainable, reproducible, and explicitly
bounded.

## 6. Target users (intended)

Intended audience for the prototype:

- building / facility engineers responsible for condition management
- retrofit planners deciding what to address first
- engineering consultancies and technical inspection services
- engineering digitalisation teams building similar internal tooling

**[limitation]** There is no real deployment and no real user. No building,
site, or organisation uses this platform. Everything runs on generated data.

## 7. Core workflow

```
Building
   ↓
Monitoring                (sensor time series)
   ↓
Anomaly Detection         (3 methods in parallel, deduplicated)
   ↓
Health Assessment         (BHI 0-100, 5 weighted dimensions)
   ↓
Risk Classification       (4 tiers + HIGH-anomaly override)
   ↓
Retrofit Decision         (RP-v1.0 priority + REC-v1.0 rules)
   ↓
Priority                  (ranked, with cost level and urgency)
   ↓
AI Explanation            (reads the results; does not compute them)
```

**[implemented]** The whole chain runs end to end and is exposed through the API
and the UI.

## 8. Main features

Stated as engineering tasks, not pages:

| Capability | Status |
|---|---|
| Monitoring analytics over sensor time series | **[implemented]** |
| Anomaly detection (absolute threshold / rate of change / z-score) | **[implemented]** **[prototype]** parameters |
| Building Health Index — 5 weighted dimensions | **[implemented]** **[prototype]** weights |
| Risk classification — 4 tiers with an override rule | **[implemented]** **[prototype]** boundaries |
| Retrofit prioritisation — RP-v1.0 + REC-v1.0 rule engine | **[implemented]** **[prototype]** weights and rules |
| Evidence traceability from recommendation back to sensor | **[implemented]** |
| Grounded AI explanation with separated evidence types | **[implemented]** |
| Engineering knowledge retrieval (RAG) over an internal corpus | **[implemented]** |
| Runtime AI safety guard and forced disclaimer | **[implemented]** |

## 9. Data model

8 tables **[implemented]**:

| Table | Role |
|---|---|
| `buildings` | Asset record: type, structure, floors, area, design life, age |
| `components` | Structural / facility elements within a building |
| `sensors` | Measurement points: metric type, unit, location, status |
| `monitoring_records` | Timestamped readings with a quality flag |
| `health_assessments` | Stored BHI results with dimension scores and version |
| `risk_alerts` | Detected anomalies with method, severity, explanation |
| `retrofit_recommendations` | Table exists; recommendations are currently computed in real time, not stored **[limitation]** |
| `engineering_notes` | Free-text engineering annotations attached to a building |

Development database: SQLite, single file.

## 10. Engineering algorithms

**[implemented]** Three anomaly detection methods run in parallel, because each
has a different blind spot:

| Method | Detects | Prototype parameters |
|---|---|---|
| Absolute threshold | Sudden excursions | crack width 0.20 / 0.30 mm · tilt 3.0 / 4.0 ‰ · temperature 40 °C · humidity 85 % |
| Rate of change | Developing trends | per-metric absolute delta and relative percentage |
| Z-score | Departure from statistical history | 7-day (168 h) rolling window · minimum 24 samples · \|z\| > 4 anomaly · \|z\| > 6 HIGH · disabled for electricity and humidity (too noisy) |

Detections are deduplicated on `(sensor, metric, method, severity)` within a
6-hour window, so one physical event does not produce a burst of alerts.

Version identifier: `ANOM-v1.0` **[prototype]**

## 11. Building Health Index (BHI)

**[implemented]** `BHI = Σ (dimension score × weight)`, range [0, 100]:

| Dimension | Weight | Input |
|---|---|---|
| Structural Safety | 0.40 | Structural anomalies (crack, tilt) |
| Facility Condition | 0.20 | Age relative to design life |
| Environmental Quality | 0.15 | Temperature and humidity stability |
| Energy Performance | 0.10 | Electricity coefficient of variation |
| Fire Safety | 0.15 | Floors and age (placeholder input) |

Weights sum to 1.0. Dimension inputs outside [0, 100] raise an error rather than
being silently clamped. **[prototype]** The weights are engineering judgement
encoded in configuration — not a national or industry standard.
Version: `BHI-v1.0`.

## 12. Risk classification

**[implemented]** Four tiers from the BHI:

| Tier | BHI range |
|---|---|
| Normal | 90–100 |
| Attention | 75–89 |
| Abnormal | 60–74 |
| HighRisk | 0–59 |

Override rule: any HIGH-severity anomaly forces a minimum of Attention,
regardless of the composite score. The rule errs toward over-alerting rather
than under-alerting. **[prototype]** Version: `RISK-v1.0`.

## 13. Retrofit priority

**[implemented]** Two prototype models:

- **RP-v1.0** — priority 0–100 from five weighted sub-scores:
  risk severity 0.35 · trend 0.25 · component importance 0.20 · urgency 0.10 ·
  cost efficiency 0.10. Banded Low / Medium / High / Very High.
- **REC-v1.0** — a rule engine producing recommendations by category, each with
  an estimated cost level and an urgency.

**[limitation]** Recommendations are computed in real time and are not
persisted, so there is no historical comparison of past recommendations.
**[limitation]** Cost is an ordinal level, not a cost estimate.

## 14. AI assistant

**[implemented]** An explanation layer over the deterministic results.
It reads the computed engineering context and explains it; it never computes.

Two provider modes:

- **Mock provider (default)** — deterministic, fully offline, no external calls.
  Used for demonstration and for the entire test suite.
- **OpenAI-compatible provider (optional)** — any OpenAI-compatible endpoint,
  configured by environment variables. No vendor SDK is installed; the call is
  plain HTTP.

Source: `backend/app/ai/`. Mock and real providers share the same runtime safety
guard and the same output schema.

## 15. RAG (engineering knowledge retrieval)

**[implemented]** A project-internal knowledge base of 5 hand-written Markdown
documents covering the platform's own concepts: anomaly detection, BHI, risk
classification, retrofit decision, and the engineering redlines. Section-based
chunking produces 23 chunks.

Retrieval is lexical and deterministic: TF-IDF with cosine similarity,
implemented in the Python standard library. No vector database, no embedding
service, no internet access. Top-3 chunks, relevance score in [0, 1].

**[limitation]** The corpus is small and covers only project-internal concepts;
it is background material, not a broad engineering reference.
**[limitation]** Chinese retrieval tokenises per character, so morphological
variation and synonyms are not handled.

## 16. Evidence chain

**[implemented]** Two distinct kinds of evidence, deliberately separated:

**Engineering evidence** — about the specific building:

```
retrofit recommendation
   → triggering anomalies → sensors → monitoring records
   → BHI dimension scores → risk tier
```

Rendered in the UI with links back to the source page.

**Knowledge evidence** — general background retrieved from the internal corpus,
fully separate in the response schema (a different field), in the prompt
(a different key), and in the UI (a different section, different colour).

They are never merged. **[implemented]** The engine data has explicit priority:
the prompt states that engineering data context has absolute priority and that
knowledge context provides background explanation only.

## 17. Performance optimisation

**[implemented]** Two rounds, each measurement-led. Local development benchmark
on an 8 GB M2 MacBook Air with SQLite, 3 buildings, 15 sensors, 1350 monitoring
records, median of 5 runs. **This is a local development benchmark, not a
production performance claim.**

Round 1 — database access. The same monitoring series was read three times per
building, and the latest assessment twice:

| Endpoint | Before | After |
|---|---|---|
| `/api/dashboard/summary` | 28 queries | 7 |
| `/api/buildings/overview` | 22 queries | 4 |
| `/api/retrofit/overview` | 64 queries | 6 |

Query count no longer grows with the number of buildings (asserted by tests).

Round 2 — duplicate computation. Profiling showed the bottleneck had moved from
database to CPU: anomaly detection was ~92 % of a dashboard response
(80.0 ms of 87.0 ms) while the batched series load was 3.0 ms. Counting
invocations instead of queries found the AI context path running anomaly
detection twice for the same building. A request-scoped analysis object now
computes it once and passes the result down:

| Path | Before | After |
|---|---|---|
| AI context build | 16 queries / 2 anomaly runs / 59.0 ms | 7 queries / **1** anomaly run / **31.5 ms** |

That is a 47 % reduction in that path's response time. Behavioural equivalence
is asserted by tests that compare the reused-analysis path against a fresh
per-building computation field by field.

**[limitation]** Different endpoints still recompute their own analysis; sharing
across requests would require caching, which is deliberately out of scope.

## 18. Testing

**[implemented]**

| Suite | Result |
|---|---|
| Backend (pytest) | **412 passed** across 28 test files |
| Frontend (Vitest + Testing Library) | **97 passed** across 15 files |
| TypeScript | 0 errors |
| Production build | passes (714 modules) |
| API smoke test | 19 / 19 endpoints responding |

Beyond ordinary unit and API coverage, the suite pins properties that are easy
to lose silently:

- frontend and backend engineering parameters cannot drift apart — the
  cross-language test compares frontend constants against the analytics
  engine's behaviour, not against copied literals
- aggregate endpoints must not grow their query count with the number of
  buildings
- batched loading must return exactly what per-item loading returned
- a reused analysis must produce identical results to a fresh computation
- anomaly detection runs once per building per request (verified by counting
  invocations)
- the AI redlines apply to both providers at runtime
- the knowledge corpus contains no standard codes and no forbidden phrases

`bash scripts/verify.sh` runs the backend tests, frontend tests, type check and
production build serially.

## 19. Security and safety

**[implemented]**

- 43 forbidden phrases are scanned on every AI response; a match raises
  `safety_violation` rather than returning the text
- the disclaimer is forced server-side; a model's own disclaimer is discarded
- the retrieved `knowledge_evidence` is forced from the retriever; anything the
  model returns is discarded
- the user question and the knowledge context are both declared untrusted in the
  system prompt
- every field is schema-validated (Pydantic) with bounded truncation
- the knowledge corpus is scanned for standard codes and forbidden phrases

**[limitation]** There is no authentication, no authorisation, no rate limiting,
and no audit log. CORS is restricted to local development origins. This is a
single-machine prototype.

## 20. Technology stack

**[implemented]** — nothing beyond this list is used.

| Layer | Technology |
|---|---|
| Frontend | React 18 · TypeScript 5 · Vite 5 · Tailwind CSS 3 · ECharts 5 · React Router 6 · axios |
| Backend | Python 3.9 · FastAPI 0.115 · SQLAlchemy 2.0 · Pydantic 2.9 · uvicorn |
| Analytics | NumPy · SciPy · pandas |
| Database | SQLite (single file, development) |
| AI | Mock provider (default) · OpenAI-compatible HTTP provider (optional) · no vendor SDK |
| Retrieval | Python standard library only (TF-IDF + cosine) |
| Testing | pytest · FastAPI TestClient · Vitest · Testing Library |

Not used: no vector database, no LangChain, no scikit-learn, no Redis, no
message queue, no cloud services. **[implemented]**

## 21. Current limitations

**[limitation]** All of the following are true today:

1. All monitoring data is **simulated**, produced by a deterministic
   time-series generator. No real building or site data is used.
2. Parameters (weights, thresholds, tier boundaries) are **prototype values**,
   not validated against real engineering cases.
3. **Single-machine prototype**: no authentication, no rate limiting, no audit
   log, no deployment.
4. **Retrofit recommendations are not persisted** — computed per request.
5. **Different endpoints recompute their own analysis**; there is no
   cross-request sharing.
6. **Retrieval is simple**: TF-IDF with per-character Chinese tokenisation, no
   stemming, no synonym handling.
7. The **fire-safety dimension is a placeholder**, derived from floors and age
   rather than real fire-system data.
8. The **`retrofit_recommendations` table is unused**.
9. **No professional engineering validation** has been performed on the
   parameters or the outputs.

## 22. Roadmap

**[roadmap]** — none of this is built.

- Integrate real monitoring data formats (CSV, standard time-series protocols)
  and define data-quality handling
- Persist retrofit recommendations as a recommendation history
- Improve retrieval: domain vocabulary, light stemming, bigram Chinese
  tokenisation
- Add authentication, project-level authorisation, and an audit log
- Production infrastructure: managed database, containerisation, secret
  management, cost tracking for the AI layer
- Professional engineering validation of parameters and outputs by qualified
  engineers

Explicitly out of scope: conversation/multi-turn, agents, MCP, function
calling, BIM/GIS, IoT/MQTT, vector databases, automatic structural design,
safety certification, and collapse prediction.

## 23. Explicit non-claims

**BuildHealth does not and will not:**

- perform a structural appraisal or issue a safety certification
- predict building collapse or structural failure
- perform automatic structural design or reinforcement design
- claim compliance with any national or industry standard
- replace a qualified structural engineer or professional inspection
- operate as a production structural safety monitoring system
- provide AI-driven structural diagnosis
- make autonomous engineering decisions

These are enforced in code — by the redline list, the forced disclaimer, the
output schema, and the corpus scan — and each is covered by tests. The project
must not be described in any way that contradicts this list.
