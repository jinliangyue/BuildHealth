# BuildHealth

**Existing Building Health Monitoring & Intelligent Retrofit Decision Platform**

*Digital civil engineering · engineering data · engineering decision support · AI-assisted explanation*

---

**What it is.** An engineering decision-support platform for monitoring,
assessing, and prioritizing retrofit actions for existing buildings.

**The problem it addresses.** Existing building stock is large and ageing, while
condition assessment still depends largely on periodic manual inspection —
costly, slow, and hard to scale. Monitoring systems can collect data
continuously, but raw sensor values are not, by themselves, a decision basis.
Between a reading and an engineering decision there is a missing layer: an
analysis layer that is explainable, reproducible, and explicitly bounded.

**What was built.** A full-stack prototype that implements that layer end to
end: a monitoring data model, three parallel anomaly-detection methods, a
weighted Building Health Index, a four-tier risk classification with an override
rule, a retrofit prioritisation model with a rule engine and an evidence chain,
and an AI explanation layer that reads the computed results and explains them.

**Why it is not just another AI dashboard.** Every engineering number is
produced by deterministic algorithms in the backend. The AI layer cannot
compute, modify, or conclude anything — it explains. The AI's disclaimer is
overwritten server-side, its citations are discarded in favour of the
retriever's, and 43 forbidden phrases are enforced at runtime. Engineering data
and retrieved knowledge are separate evidence types in the schema, in the prompt
and in the UI.

> **Prototype notice.** All monitoring data is simulated. All parameters are
> prototype values, not national or industry standards. This is a
> decision-support prototype, not a structural appraisal, certification, or
> safety monitoring system.

---

## 1. Overview

BuildHealth explores how digital monitoring and data-driven analysis can support
the assessment and prioritization of retrofit actions for existing buildings.

The platform treats condition management as a traceable chain rather than a
single score. A building record defines the asset; sensors define the
measurement points; timestamped readings feed three anomaly-detection methods
that run in parallel because each has a different blind spot — absolute
thresholds catch sudden excursions, rate-of-change catches developing trends,
and z-scores catch departures from statistical history. Deduplicated detections
then drive a weighted health index, which drives a risk tier, which drives a
ranked retrofit decision with an evidence chain back to the originating sensor.

The design constraint that shapes everything else is one-way data flow:
deterministic algorithms compute, and the AI layer explains. The AI is useful
precisely because it is not trusted with the number.

## 2. Engineering workflow

```
Building                     asset record
   ↓
Monitoring                   sensor time series + anomaly overlay
   ↓
Anomaly Detection            threshold · rate of change · z-score, deduplicated
   ↓
Health Assessment            BHI 0-100 over 5 weighted dimensions
   ↓
Risk Classification          4 tiers + HIGH-anomaly override
   ↓
Retrofit Decision            RP-v1.0 priority + REC-v1.0 rules + evidence chain
   ↓
Priority                     ranked, with cost level and urgency
   ↓
AI Explanation               grounded in the computed results only
```

The same chain is exposed through 19 HTTP endpoints and an 8-page dashboard.

## 3. Key capabilities

Stated as engineering tasks rather than pages:

- **Monitoring analytics** — time-series querying and trend visualisation over
  sensor data, with anomaly points overlaid on the series.
- **Anomaly detection** — three methods in parallel with severity-based
  deduplication, so one physical event does not produce a burst of alerts.
- **Building Health Index** — a 0–100 composite over five weighted dimensions,
  with dimension inputs validated rather than silently clamped.
- **Risk classification** — four tiers with a conservative override rule: a
  HIGH-severity anomaly forces a minimum tier regardless of the composite score.
- **Retrofit prioritisation** — a weighted priority model plus a rule engine
  producing categorised recommendations with cost level and urgency.
- **Evidence traceability** — every recommendation can be traced back through
  its triggering anomalies to the originating sensor, and the UI links back.
- **Grounded AI explanation** — natural-language explanation of computed
  results, with engineering evidence and knowledge evidence kept separate.
- **Engineering knowledge retrieval** — deterministic lexical retrieval over a
  project-internal knowledge base of platform concepts.

## 4. Engineering analytics

All parameters live in `backend/app/analytics/config.py`, carry version
identifiers, and are exposed read-only through
`GET /api/engineering-parameters`. They are **prototype design parameters**, not
national or industry standards, and the platform says so wherever they appear.

**Anomaly detection** — three methods, run in parallel:

| Method | Detects | Prototype parameters |
|---|---|---|
| Absolute threshold | Sudden excursions | crack width 0.20 / 0.30 mm · tilt 3.0 / 4.0 ‰ · temperature 40 °C · humidity 85 % |
| Rate of change | Developing trends | per-metric absolute delta and relative percentage |
| Z-score | Departure from statistical history | 7-day rolling window · min 24 samples · \|z\| > 4 anomaly · \|z\| > 6 HIGH · disabled for electricity and humidity |

Detections are deduplicated on `(sensor, metric, method, severity)` within a
6-hour window.

**Building Health Index (BHI-v1.0)** — `BHI = Σ (dimension score × weight)`:

| Dimension | Weight | Input |
|---|---|---|
| Structural Safety | 0.40 | Structural anomalies |
| Facility Condition | 0.20 | Age relative to design life |
| Environmental Quality | 0.15 | Temperature and humidity stability |
| Energy Performance | 0.10 | Electricity coefficient of variation |
| Fire Safety | 0.15 | Floors and age (placeholder input) |

**Risk classification (RISK-v1.0)** — `≥ 90` Normal · `≥ 75` Attention ·
`≥ 60` Abnormal · `< 60` HighRisk. A HIGH-severity anomaly forces a minimum of
Attention. The rule errs toward over-alerting rather than under-alerting.

**Retrofit priority (RP-v1.0 / REC-v1.0)** — priority 0–100 from five weighted
sub-scores (risk severity 0.35 · trend 0.25 · component importance 0.20 ·
urgency 0.10 · cost efficiency 0.10), banded Low → Very High, plus a rule engine
producing categorised recommendations with cost level and urgency.

## 5. AI architecture

The AI is not the engineering core. It sits at the end of the chain:

```
Engineering data
    ↓
Deterministic analysis        (anomaly → health → risk → retrofit)
    ↓
Computed results
    ↓
AI explanation                (reads only; never computes)
```

**Providers.** A deterministic mock provider is the default: fully offline, no
external calls, used for the whole test suite. An optional OpenAI-compatible
provider talks to any compatible endpoint over plain HTTP — no vendor SDK is
installed. Both share the same runtime safety guard and the same output schema.

**Retrieval (RAG).** A project-internal knowledge base of five hand-written
documents on the platform's own concepts, chunked by section into 23 chunks.
Retrieval is TF-IDF with cosine similarity, implemented in the Python standard
library — no vector database, no embedding service, no internet access. The
choice is deliberate: the requirement is offline, deterministic and explainable,
and at this corpus size a vector index would add infrastructure without adding
retrieval quality.

**Evidence separation.** Engineering evidence (about this building) and
knowledge evidence (general background) are separate fields in the response
schema, separate keys in the prompt, and separate sections in the UI. The prompt
states that engineering data has absolute priority and that knowledge provides
background explanation only.

**Runtime safety.** 43 forbidden phrases are scanned on every response and a
match raises `safety_violation`; the disclaimer is forced server-side; the
retrieved knowledge evidence is forced from the retriever, discarding anything
the model returns; the user question and the knowledge context are both declared
untrusted.

## 6. Performance engineering

Two optimisation rounds, each measurement-led. Numbers below are a **local
development benchmark** on an 8 GB M2 MacBook Air with SQLite, 3 buildings,
15 sensors and 1350 monitoring records, median of 5 runs. They are not a
production performance claim.

**Round 1 — database access.** Measurement showed the same monitoring series
being read three times per building, the latest assessment queried twice, and
per-sensor queries where one would do. Batching removed the N+1:

| Endpoint | Before | After |
|---|---|---|
| `/api/dashboard/summary` | 28 queries | 7 |
| `/api/buildings/overview` | 22 queries | 4 |
| `/api/retrofit/overview` | 64 queries | 6 |

Query count no longer grows with the number of buildings, and this is asserted
by tests rather than assumed.

**Round 2 — duplicate computation.** After batching, response time barely moved,
so the bottleneck was profiled directly: anomaly detection accounted for 80.0 ms
of an 87.0 ms dashboard response (~92 %), while the batched series load was
3.0 ms. The bottleneck had moved from database to CPU. Counting *invocations*
instead of queries found the real defect — the AI context path ran anomaly
detection twice for the same building, discarding the second result.

A request-scoped analysis object now computes each building's chain once and
passes it down the call stack:

| Path | Before | After |
|---|---|---|
| AI context build | 16 queries · 2 anomaly runs · 59.0 ms | 7 queries · **1** anomaly run · **31.5 ms** |

That is roughly a **47 % reduction** in that path's response time.

Behavioural equivalence is asserted, not assumed: tests compare the
reused-analysis path against a fresh per-building computation field by field,
and the guard itself was mutation-tested.

## 7. Traceability

Every engineering result can be traced back to data:

```
Building → Sensor → Monitoring Record → Anomaly → Health → Risk → Retrofit
                                                                     ↓
                                                          Engineering Evidence
                                                          (about this building)

Knowledge Base → Retriever → Knowledge Evidence
                             (general background — NOT about this building)
```

Each layer carries a version identifier — `BHI-v1.0`, `RISK-v1.0`, `ANOM-v1.0`,
`RP-v1.0`, `REC-v1.0`, `AI-v1.0` — so a past result can be interpreted against
the parameters that produced it. **Engineering evidence and knowledge evidence
are never merged.**

## 8. Safety boundaries

**This prototype does not and will not:**

- perform a structural appraisal or issue a safety certification
- predict building collapse or structural failure
- perform automatic structural design or reinforcement design
- claim compliance with any national or industry standard
- replace a qualified structural engineer or professional inspection
- provide AI-driven structural diagnosis or make autonomous engineering decisions

These are not disclaimers bolted on at the end. They are enforced by the redline
list, the forced disclaimer, the output schema and the knowledge-corpus scan —
and each is covered by tests. The AI cannot override deterministic engineering
results: its disclaimer is overwritten, its citations are discarded, and its
output is scanned and schema-validated before it is returned.

**All data is simulated.** No real building, site or organisation is monitored.
A permanent watermark marks the dataset as simulated, and a dedicated page
documents the data source.

## 9. Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18 · TypeScript 5 · Vite 5 · Tailwind CSS 3 · ECharts 5 · React Router 6 · axios |
| Backend | Python 3.9 · FastAPI 0.115 · SQLAlchemy 2.0 · Pydantic 2.9 · uvicorn |
| Analytics | NumPy · SciPy · pandas |
| Database | SQLite (single development file) |
| AI | Mock provider (default) · OpenAI-compatible HTTP provider (optional) · no vendor SDK |
| Retrieval | Python standard library only (TF-IDF + cosine) |
| Testing | pytest · FastAPI TestClient · Vitest · Testing Library |

No vector database, no LangChain, no scikit-learn, no Redis, no message queue,
no cloud services.

## 10. Testing

| Suite | Result |
|---|---|
| Backend | **478 passed, 5 skipped** (33 `test_*.py` files; pytest collects 483 = 478 passed + 5 deepeval-live skipped) |
| Frontend | **97 passed** (15 test files) |
| TypeScript | 0 errors (`tests/` included since 2026-10-16) |
| Production build | passes (`vite build` ✓; **716 modules transformed** · chunk 1,354 KB) |
| API smoke test | **21 / 21 endpoints responding** (incl. audit log; verified on real `uvicorn`) |
| Line coverage (backend) | **95 %** of `app/` (2,465 statements · 125 missing · TOTAL 95 %) — config in `backend/.coveragerc`; XML + HTML reports on every CI run |

Coverage extends beyond ordinary unit and API tests to properties that are easy
to lose silently:

- **equivalence** — batched and reused computations must return exactly what
  per-item computation returned
- **parameter consistency** — frontend and backend engineering parameters cannot
  drift apart, checked against the engine's behaviour rather than copied values
- **anomaly reuse** — anomaly detection runs once per building per request,
  verified by counting invocations
- **query count** — aggregate endpoints must not grow their query count with the
  number of buildings
- **AI safety** — redlines apply to both providers at runtime
- **RAG** — the corpus contains no standard codes and no forbidden phrases
- **API behaviour** — endpoint contracts, error paths and response shapes

The backend test run uses `pytest-cov` (pinned in `requirements.txt`) with
configuration in `.coveragerc`. Coverage is **reported, not enforced** —
no `fail-under` threshold, because at this scale a missed defensive branch
on a misconfigured deployment is more annoying than informative. CI uploads
`coverage.xml` and `htmlcov/` as a 14-day artifact from the Python 3.11
matrix leg; download it from the Actions run summary to inspect the HTML
report locally.

```bash
bash scripts/verify.sh                                          # backend tests → frontend tests → tsc → build
pytest --cov=app --cov-report=term-missing --cov-report=html    # coverage + HTML report (open htmlcov/index.html)
```

## 11. Limitations

Honest list of what is not there yet:

- **Simulated data only.** No real monitoring data has been integrated.
- **Prototype parameters.** Weights, thresholds and tier boundaries are
  engineering judgement encoded in config, not validated against real cases.
- **Single-machine prototype.** No authentication, no rate limiting, no audit
  log, no deployment.
- **Recommendations are not persisted** — computed per request.
- **Different endpoints recompute their own analysis.** Sharing across requests
  would require caching, which is deliberately out of scope.
- **Simple retrieval.** TF-IDF with per-character Chinese tokenisation; no
  stemming, no synonym handling.
- **Fire-safety dimension is a placeholder**, derived from floors and age rather
  than real fire-system data.
- **No professional engineering validation** has been performed on the
  parameters or the outputs.

## 12. External validation

Anomaly detection methods were evaluated against the
[NAB (Numenta Anomaly Benchmark)](https://github.com/numenta/NAB)
public dataset — 58 labeled time series, 52 with anomaly windows.

| Method | Precision | Recall | F1 |
|---|---|---|---|
| **Combined (union)** | 0.182 | **0.152** | **0.152** |
| Rolling MAD | 0.324 | 0.135 | 0.146 |
| Threshold (percentile) | 0.188 | 0.121 | 0.132 |
| Z-score (7d) | 0.456 | 0.036 | 0.075 |
| Isolation Forest | 0.376 | 0.037 | 0.068 |
| Rate of Change | 0.185 | 0.029 | 0.046 |
| Naive (1% random) | 0.102 | 0.009 | 0.017 |

Combined (BuildHealth's actual architecture) achieves the highest F1,
outperforming any single method and 9× the naive baseline. Full
methodology and what to put in a résumé vs avoid saying is in
[`docs/30_NAB_External_Evaluation.md`](docs/30_NAB_External_Evaluation.md).

Reproduce with: `bash scripts/verify_benchmarks.sh`

## 13. Roadmap

Not built — direction only:

- Integrate real monitoring data formats and define data-quality handling
- Persist retrofit recommendations as a recommendation history
- Improve retrieval: domain vocabulary, light stemming, bigram Chinese
  tokenisation
- Add authentication, project-level authorisation, and an audit log
- Production infrastructure: managed database, containerisation, secret
  management, AI cost tracking
- Professional engineering validation of parameters and outputs

**Explicitly out of scope:** conversation/multi-turn, agents, MCP, function
calling, BIM/GIS, IoT/MQTT, vector databases, automatic structural design,
safety certification, collapse prediction.

---

## Repository layout

```
BuildHealth/
├── backend/
│   ├── app/
│   │   ├── analytics/     anomaly · health · risk · priority · recommendation rules
│   │   ├── api/           FastAPI routers (19 endpoints)
│   │   ├── services/      orchestration between API and analytics
│   │   ├── ai/            providers · context builder · redlines · RAG integration
│   │   ├── knowledge/     loader · chunker · retriever
│   │   └── db/            SQLAlchemy models and session
│   ├── knowledge/         internal engineering knowledge base (5 documents)
│   ├── scripts/           seed data · benchmarks · retrieval eval
│   └── tests/             28 test files
├── frontend/
│   ├── src/               React app (8 pages, components, api client, hooks)
│   └── tests/             15 test files
├── docs/                  design, testing and architecture documentation
├── benchmark/external/    NAB anomaly-detection benchmark
├── scripts/verify.sh      one-command local verification (backend + frontend + build)
├── scripts/verify_benchmarks.sh  opt-in NAB regression check
├── Dockerfile.backend     Python 3.11-slim image for FastAPI + SQLite
├── Dockerfile.frontend    multi-stage build → nginx serving the Vite bundle
├── nginx.conf             SPA fallback + /api proxy to backend service
└── docker-compose.yml     one-shot local stack on http://localhost:8080
```

## Running locally

Two ways: native (for development with hot-reload) or Docker (for a clean
end-to-end smoke test that mirrors how the app actually runs).

### Native (development with hot-reload)

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m scripts.seed_data          # generate simulated data (wipes the DB)
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

### Docker (one-shot stack)

The stack runs both services on an internal Docker network. The frontend
container reverse-proxies `/api/*` to the backend, so from the browser you
only need one origin: <http://localhost:8080>.

```bash
# First run — builds images, seeds the SQLite database, starts both services
docker compose up --build

# Detached after the first build
docker compose up -d

# Open
open http://localhost:8080           # frontend (nginx)
curl http://localhost:8000/api/health  # backend directly, if you need it

# Tear down (keep the DB volume for next time)
docker compose down

# Tear down AND wipe the simulated data
docker compose down -v
```

Images are built from `Dockerfile.backend` (Python 3.11-slim, ~400 MB) and
`Dockerfile.frontend` (multi-stage Node → nginx:alpine, ~40 MB). The backend
runs `scripts.seed_data` automatically on first start via
`backend/docker-entrypoint.sh`; subsequent restarts skip seeding.

**Switching to a real LLM provider.** The default provider in Docker is
`mock` (no API key required). To use an OpenAI-compatible endpoint, set
`AI_PROVIDER=openai-compatible`, `AI_BASE_URL`, and `AI_API_KEY` in the
`backend.environment` block of `docker-compose.yml` (or via an `.env` file).

> Both modes seed the same simulated dataset. The data is regenerated every
> time `scripts.seed_data` runs, so `docker compose down -v && up --build`
> gives you a clean slate.

### One-command verification

```bash
bash scripts/verify.sh              # backend tests + frontend tests + tsc + production build
bash scripts/verify_benchmarks.sh   # opt-in: NAB external benchmark regression check
```

## Documentation

`docs/` holds the design and engineering record. The most useful entry points:

| Document | Content |
|---|---|
| `01_Project_Overview.md` | Project scope and principles |
| `03_System_Architecture.md` | Module boundaries and data flow |
| `05_Analytics_Design.md` | Anomaly detection and BHI design |
| `19_Engineering_RAG.md` | Knowledge base and retrieval design |
| `20_AI_Grounding_and_Safety.md` | Evidence separation and safety model |
| `architecture.md` | Architecture diagrams |
| `28_Project_Fact_Sheet.md` | Verified fact baseline for anything written about the project |

Some design documents are written in Chinese; the code, this README, and the
fact sheet are in English.

## License

Private / prototype project.
