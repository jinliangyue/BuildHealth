# 29 · 30-Second Overview

> **Internal preparation note — not project documentation.**
> This file exists to prepare a spoken summary. It is not part of the project's
> narrative and is not referenced from the README. The project itself is
> presented on its engineering merits only (`README.md`,
> `28_Project_Fact_Sheet.md`).

One page. Readable in 30 seconds.

---

## Project

**BuildHealth** — Existing Building Health Monitoring & Intelligent Retrofit
Decision Platform.

A digital decision-support prototype for existing buildings: it takes monitoring
data through anomaly detection, health assessment, risk classification and
retrofit prioritisation, and explains the results in plain language.

## Problem

Existing buildings age, but condition assessment still depends largely on
periodic manual inspection. Monitoring systems collect data continuously, yet
raw sensor values are not a decision basis on their own. What is missing between
a reading and an engineering decision is an analysis layer that is explainable,
reproducible and explicitly bounded.

## Solution

BuildHealth implements that layer end to end:

```
Building → Monitoring → Anomaly → Health → Risk → Retrofit → AI explanation
```

Three anomaly-detection methods run in parallel, feed a weighted 0–100 Building
Health Index, which feeds a four-tier risk classification with a conservative
override rule, which feeds a weighted retrofit priority and a rule engine that
produces ranked recommendations — each traceable back to the sensor that
triggered it.

## Engineering

- **Anomaly detection**: absolute threshold, rate of change, and z-score over a
  7-day rolling window, deduplicated by severity so one event is one alert.
- **BHI**: five weighted dimensions (structural safety 0.40, facility 0.20,
  environment 0.15, energy 0.10, fire safety 0.15), inputs validated rather than
  clamped.
- **Risk**: four tiers plus an override — any HIGH-severity anomaly forces a
  minimum tier, erring toward over-alerting.
- **Retrofit**: priority from five weighted sub-scores, plus a rule engine
  producing recommendations with cost level and urgency.
- **Parameters are prototype values**, served read-only from the backend and
  labelled as such everywhere they appear.

## Technology

React · TypeScript · Vite · Tailwind · ECharts on the front end; Python ·
FastAPI · SQLAlchemy · Pydantic with NumPy / SciPy / pandas behind it; SQLite
for storage.

The AI layer sits at the end of the chain: a deterministic offline provider by
default, an optional OpenAI-compatible provider over plain HTTP, and a
standard-library TF-IDF retriever over an internal knowledge base. No vector
database, no LangChain, no cloud services.

## Result

Working full-stack prototype: 19 API endpoints, 8 pages, 8 database tables.
**412 backend tests** and **97 frontend tests** pass; TypeScript clean;
production build passes; all 19 endpoints verified.

Performance work was measurement-led: batching removed an N+1 (28 → 7 queries on
the dashboard), then profiling showed the bottleneck had moved to CPU, and a
request-scoped reuse cut the AI context path from 59.0 ms to 31.5 ms.

## My role

Designed the engineering workflow and data model, implemented the analytics
engine and the API, built the frontend, and wrote the safety model and the test
suite. AI-assisted development accelerated the implementation; the engineering
decisions — what is computed, what is explained, and what is refused — came from
the domain constraints.

## One-line pitch

> I built an engineering decision-support platform that turns building monitoring
> data into a traceable assessment and retrofit priority — with deterministic
> engineering algorithms doing the computation and AI confined to explaining
> them.
