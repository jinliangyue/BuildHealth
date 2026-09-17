# 32 · Interview Redlines

> **Internal preparation note — not project documentation.**
> Statements that would not survive follow-up questions, with a defensible
> replacement. These are about being accurate under pressure, not about
> softening the project.
>
> The rule behind every row: **say what the code does, not what it sounds like
> it could do.**

---

## 1. Collapse and failure prediction

| Don't say | Say instead |
|---|---|
| "This system predicts structural collapse." | "This prototype identifies abnormal monitoring trends and supports engineering review. It does not predict failure." |

*Why:* there is no failure model, no labelled outcome data, and no validation.
Any follow-up question about prediction accuracy would be unanswerable.

## 2. AI performing structural diagnosis

| Don't say | Say instead |
|---|---|
| "The AI performs structural diagnosis." | "The AI explains deterministic engineering analysis results. All computation happens in the analytics engine." |

*Why:* the AI reads a typed context and produces text. It has no access to raw
records and cannot modify any computed value.

## 3. Safety certification

| Don't say | Say instead |
|---|---|
| "It certifies whether a building is safe." | "It classifies prototype risk tiers to help prioritise review. It does not certify safety." |

*Why:* the tier is a prototype parameter set (`RISK-v1.0`), and the system has
no authority or validation to certify anything.

## 4. Compliance with standards

| Don't say | Say instead |
|---|---|
| "The thresholds comply with building standards." | "The thresholds are prototype design parameters. They are not derived from, and make no claim to, any national or industry standard." |

*Why:* the parameters are engineering judgement in a config file. The corpus is
also scanned to guarantee no standard codes appear anywhere.

## 5. Real deployment

| Don't say | Say instead |
|---|---|
| "It's deployed on building monitoring systems." | "It's a single-machine prototype running on simulated data. No real building or site is monitored." |

*Why:* no deployment exists. There is no authentication, no rate limiting and no
audit log, and the data is generated.

## 6. Real buildings / real users

| Don't say | Say instead |
|---|---|
| "It monitors several buildings." | "It runs on a generated dataset of three buildings, fifteen sensors and 1,350 records, designed to exercise the analysis chain." |

*Why:* the buildings are named "Building A · Healthy Tower", "Building B ·
Attention Plaza", "Building C · Abnormal Complex" — a demo dataset, not assets.

## 7. Production readiness

| Don't say | Say instead |
|---|---|
| "It's production-ready." | "It's a working prototype. Production would need authentication, an audit log, real data ingestion, and professional validation of the parameters." |

*Why:* the honest gap list is short and specific, and naming it is more
convincing than avoiding the question.

## 8. Performance benchmarks

| Don't say | Say instead |
|---|---|
| "It's 47% faster in production." | "In a local development benchmark on an 8 GB M2 Air with SQLite and a 3-building dataset, the AI context path went from 59.0 ms to 31.5 ms — median of five runs." |

*Why:* the measurement is real but the environment is a laptop and the dataset
is small. Presenting it as a production figure invites a question you can't
answer.

## 9. Scale claims

| Don't say | Say instead |
|---|---|
| "It scales to thousands of buildings." | "Query count no longer grows with the number of buildings — that's asserted by tests. But the system has only been exercised on three, and single-machine SQLite would be the next constraint." |

*Why:* the batching work is real and tested; the scalability claim is not.
Separate the two.

## 10. Machine learning

| Don't say | Say instead |
|---|---|
| "It uses machine learning to detect anomalies." | "Anomaly detection uses three statistical methods — absolute threshold, rate of change, and z-score. No model is trained and there is no ML dependency." |

*Why:* scikit-learn is not even installed. Every detection is explainable
arithmetic, which is a deliberate choice, not a limitation to apologise for.

## 11. Embeddings / vector search

| Don't say | Say instead |
|---|---|
| "It uses vector embeddings for semantic search." | "Retrieval is lexical — TF-IDF with cosine similarity, standard library only. No vector database and no embedding model." |

*Why:* the choice is deliberate (offline, deterministic, explainable) and
defensible. Claiming embeddings would be both false and a weaker argument.

## 12. Accuracy figures

| Don't say | Say instead |
|---|---|
| "It's 95% accurate." | "There is no accuracy figure. The parameters are prototype values and have not been validated against real inspection outcomes." |

*Why:* nothing in the project has been measured against ground truth, because
there is no ground truth.

## 13. Professional validation

| Don't say | Say instead |
|---|---|
| "The method was reviewed by engineers." | "The parameters are my engineering judgement encoded in configuration. They have not been professionally validated — that's on the roadmap." |

*Why:* no review has occurred. Saying it happened would be a fabrication that a
follow-up question exposes immediately.

## 14. Autonomous engineering decisions

| Don't say | Say instead |
|---|---|
| "The system makes retrofit decisions autonomously." | "It ranks and explains candidate actions. The decision stays with the engineer — the output is decision support." |

*Why:* the system produces a ranking and a rationale. It takes no action and
has no authority.

## 15. Automatic structural design

| Don't say | Say instead |
|---|---|
| "It generates retrofit designs." | "It produces categorised recommendations with a cost level and urgency. It does not generate designs, reinforcement details, or drawings." |

*Why:* the rule engine emits text recommendations from templates, not
engineering design output.

## 16. Real-time capability

| Don't say | Say instead |
|---|---|
| "It monitors buildings in real time." | "It analyses stored time-series data on request. There is no streaming, no live sensor connection and no IoT integration." |

*Why:* there is no MQTT, no device layer, no streaming. The dashboard has an
auto-refresh, which is not the same thing.

## 17. "The AI is the product"

| Don't say | Say instead |
|---|---|
| "It's an AI platform for buildings." | "The AI is an explanation layer at the end of a deterministic chain. The engineering value is in the analytics — anomaly detection, BHI, risk, and retrofit priority." |

*Why:* leading with AI misrepresents where the engineering work is and invites
questions about a component that is deliberately constrained.

## 18. "It replaces inspection"

| Don't say | Say instead |
|---|---|
| "It replaces manual inspection." | "It's decision support that can help prioritise where inspection effort goes. It doesn't replace inspection or professional judgement." |

*Why:* replacement overstates both the capability and the intent.

## 19. Knowledge base authority

| Don't say | Say instead |
|---|---|
| "The AI cites engineering standards." | "The AI retrieves from a five-document internal knowledge base describing this platform's own concepts. It contains no standard codes and is explicitly not an authority." |

*Why:* the corpus is scanned by a test to guarantee it contains no standard
codes and no forbidden phrases. It is background, not reference material.

## 20. Evidence conflation

| Don't say | Say instead |
|---|---|
| "The AI retrieves evidence about the building." | "Two evidence types are kept separate: engineering evidence about this building, and knowledge evidence providing general background. They're different fields, different prompt keys, and different UI sections." |

*Why:* this separation is a core design property and a likely follow-up
question. Conflating them in the explanation would contradict the code.

---

## The general rule

If a sentence would need a qualifier to be true, put the qualifier in the first
version. Every claim here is checked against `28_Project_Fact_Sheet.md`, and
anything contradicting section 23 of that document ("Explicit non-claims")
should not be said at all.
