# 31 · Project Interview Opening

> **Internal preparation note — not project documentation.**
> Spoken answers to open the project discussion. Not part of the project's
> narrative and not referenced from the README.
>
> The "why" answers use neutral wording because no personal motivation is
> documented. If you have your own genuine reason for starting the project,
> **replace it with that** — do not deliver a rationale you cannot stand behind.

---

## 30-second version

> BuildHealth is a decision-support prototype for existing buildings. It takes
> monitoring data — crack width, tilt, temperature, humidity, electricity —
> through anomaly detection, a weighted health index, risk classification, and
> retrofit prioritisation, and then explains the results in plain language.
>
> The part I care about is the boundary: every engineering number is computed by
> deterministic algorithms in the backend, and the AI is only allowed to explain
> them. It can't compute, and it can't conclude. That constraint shapes the whole
> design.

**Why did you build it?**
> I wanted to work on the layer between a sensor reading and an engineering
> decision. Monitoring hardware is increasingly common, but the data it produces
> isn't a decision basis on its own — there's an analysis gap, and that's the
> interesting engineering problem.

**What did you personally do?**
> Everything: the data model, the analytics engine, the API, the frontend, the
> safety model, and the test suite. AI-assisted development sped up the
> implementation, but the engineering decisions — what gets computed, what gets
> explained, and what the system refuses to say — came from the domain side.

---

## 60-second version

> BuildHealth is a digital decision-support platform for existing buildings.
> Existing stock is large and ageing, and condition assessment still depends
> heavily on periodic manual inspection — expensive and hard to scale. Monitoring
> systems give you continuous data, but raw values aren't a decision basis.
>
> So I built the analysis layer in between. Data flows through three anomaly
> detection methods running in parallel — absolute threshold, rate of change, and
> z-score — because each has a different blind spot. Detections are deduplicated
> by severity so one physical event doesn't produce a burst of alerts. That feeds
> a Building Health Index over five weighted dimensions, then a four-tier risk
> classification with a conservative override rule, then a retrofit priority
> model and a rule engine that produces ranked recommendations.
>
> Every recommendation can be traced back to the sensor that triggered it.
>
> The design constraint is one-way data flow: deterministic algorithms compute,
> and the AI explains. The AI's disclaimer is overwritten server-side, its
> citations are discarded in favour of the retriever's, and 43 forbidden phrases
> are blocked at runtime.
>
> **What was technically difficult?** Two things. Getting the parameters to
> stay honest — the same thresholds were living in several places, so I added a
> test that checks the frontend's values against the engine's *behaviour*, not
> against copied numbers. And the performance work, which I'll come back to.

**What did you learn?**
> That measurement has to drive optimisation, and that the metric has to change
> when the bottleneck moves. I optimised the database access first, and the
> response time barely moved — because the bottleneck had already shifted to CPU.
> I only found the real problem when I stopped counting queries and started
> counting how many times the same computation was triggered.

---

## 3-minute version

**Framing (20s)**

> BuildHealth is an engineering decision-support prototype for existing
> buildings. The engineering problem is this: building stock is ageing, manual
> inspection is costly and infrequent, and monitoring systems produce continuous
> data that isn't a decision basis by itself. There's a missing analysis layer
> between a reading and a decision — explainable, reproducible, and explicitly
> bounded. That's what I built.

**The chain (40s)**

> The workflow is a chain, not a single score. A building record defines the
> asset; sensors define measurement points; timestamped readings feed three
> anomaly detection methods in parallel — absolute threshold catches sudden
> excursions, rate of change catches developing trends, z-score catches departures
> from statistical history. Each has a blind spot, so all three run and the
> detections are deduplicated on sensor, metric, method and severity within a
> six-hour window.
>
> That feeds a Building Health Index — 0 to 100 over five weighted dimensions,
> with structural safety at 0.40. Then a four-tier risk classification with an
> override: any HIGH-severity anomaly forces a minimum tier, so a good aggregate
> score can't hide a serious local defect. Then a retrofit priority from five
> weighted sub-scores, a rule engine that produces categorised recommendations,
> and an evidence chain back to the originating sensor.

**What I personally did (30s)**

> I designed the workflow and the data model, implemented the analytics engine,
> the service layer and 19 API endpoints, built the frontend, and wrote the
> safety model and the test suite. The AI-assisted development path accelerated
> the implementation a lot, but the architecture — where the boundary between
> computation and explanation sits — is the part I'd defend.

**What was technically difficult (50s)**

> Two things.
>
> First, keeping the engineering parameters honest. The same thresholds and
> weights were being displayed on the frontend and used by the backend engine.
> They agreed at the time, but nothing stopped them drifting. I gave the backend
> a read-only parameters endpoint and demoted the frontend copy to an offline
> fallback, and then wrote a cross-language test that compares the frontend's
> declared values against the engine's *actual behaviour* — it probes the
> classification function at every band boundary. Copying the numbers into a test
> would have proved nothing.
>
> Second, the performance work, which taught me the most. I measured query counts
> first and found a real N+1 — the same monitoring series was being read three
> times per building. I batched it: the dashboard went from 28 queries to 7, the
> retrofit overview from 64 to 6, and the counts stopped scaling with the number
> of buildings. But the response time barely moved. So I profiled properly and
> found anomaly detection was about 92% of the response — the bottleneck had
> moved from database to CPU. I'd been optimising the wrong thing.
>
> So I changed the metric: instead of counting queries, I counted how many times
> anomaly detection was triggered. That immediately showed the AI context path
> was running it twice for the same building and throwing the second result away.
> Computing it once per request and passing it down cut that path from 59
> milliseconds to 31.5 — about 47%.

**What I learned (40s)**

> Three things I'd carry forward.
>
> Measurement first, and be willing to change the metric. My first round of
> optimisation was correct but incomplete, because I kept measuring the thing
> that had already been fixed.
>
> Equivalence has to be proven, not assumed. For the reuse work I wrote tests
> that run the same building through both the old path and the new one and
> compare field by field — and I mutation-tested the guard to confirm it actually
> fails when the optimisation is removed. A test that can't fail isn't a test.
>
> And restraints are design decisions. The system refuses to predict collapse, to
> perform an appraisal, or to generate a structural design — and those refusals
> are enforced in code and covered by tests, not written in a disclaimer at the
> bottom of a page. Knowing what the tool should not do turned out to be as much
> of the engineering as knowing what it should.

---

## Delivery notes

- Lead with the engineering problem, not the technology stack.
- The performance story is the strongest technical narrative — it has
  measurement, a wrong turn, a correction, and a verified result.
- When asked about the AI: the interesting part is the constraint, not the
  capability. Say what it is not allowed to do before saying what it does.
- Do not claim real deployment, real buildings, real users, or professional
  validation. If asked, say plainly that the data is simulated and the
  parameters are prototype values.
- If asked "is this production-ready?" — no, and it isn't meant to be. Say what
  is missing: authentication, audit logging, real data ingestion, professional
  validation of the parameters.
