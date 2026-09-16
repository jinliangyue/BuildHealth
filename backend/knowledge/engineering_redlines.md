<!--
title: Engineering Redlines
purpose: Mandatory list of statements the system must never make, and required disclaimers.
source: BuildHealth Internal Engineering Notes
-->

# Engineering Redlines

> **BuildHealth Internal Engineering Notes** · Prototype
> These are hard redlines enforced by automated tests. Any
> architectural change that violates a redline must be rejected.

## What the System Must Never Say

The AI Engineering Assistant, the BHI explanation layer, the risk
classification, and the retrofit decision layer are all prohibited
from producing the following kinds of statements, regardless of how
the data is phrased:

- Claims that the building is safe or unsafe in absolute terms.
- Claims that the building will collapse, that the structure will
  fail, or that structural failure is certain.
- Claims that AI predicts structural failure.
- Claims that an automatic structural appraisal was completed.
- Claims of official safety certification or that a safety
  certification was issued.
- Claims of real-world deployment or that the system is in
  production.
- Claims of automatic reinforcement design, AI-designed
  reinforcement, or auto-generated structural design.
- Claims that a professional inspection was completed without the
  qualifier "qualified".
- Claims that an engineer has approved.
- Claims of compliance with any national or industry standard, in
  any language.
- Guarantees of safety in any form.
- Claims that a recorded or monitored building is a real building
  or a real monitoring deployment.

Knowledge-document-specific phrasings (Phase 6B) that are also
forbidden in AI output:

- Phrasings that assert a knowledge document proves or confirms a
  condition in the current building.
- Phrasings that present a knowledge document as an official
  specification.
- Phrasings that treat a retrieved knowledge document as an authority
  in place of a real engineering standard.
- Phrasings that put a knowledge document ahead of the measured
  engineering data for the building.
- Phrasings that treat general knowledge as taking precedence over
  engineering data.
- Phrasings that state a certification conclusion derived from
  knowledge documents rather than from qualified review.

Note that the literal banned strings themselves are not reproduced
here on purpose: `knowledge/` is scanned by
`tests/test_rag_redlines.py` for the same phrases that the AI output
scanner uses, so that the corpus can never carry a banned string.

## What the System Must Always Say

- "Prototype Design Parameters" (when describing BHI, RP, REC, anomaly
  thresholds).
- "Prototype Risk Classification, not a legally binding building
  safety grade".
- "Qualified professional review is required".
- For AI output: a fixed disclaimer appears in every response
  declaring the output is engineering decision support, not
  professional engineering appraisal.

## Why These Are Redlines

The system is a **decision-support prototype**, not a regulatory or
certification tool. If it is ever used to justify a real-world
intervention without qualified review, the lack of redlines would be
a public-safety risk. The redlines ensure that any plausible reading
of the output still defers to qualified professionals.

## Enforcement

The redlines are enforced by:
- `backend/tests/test_engineering_redlines.py` — scans backend
  source code for the same forbidden phrases (excluding the meta
  `redlines.py` itself).
- `backend/tests/test_ai_redlines.py` — scans Mock provider output
  for forbidden phrases, parametrized over 3 building profiles.
- `backend/tests/test_rag_redlines.py` — scans Real provider output
  with the same list, plus the RAG-specific phrasings.
- AI_RESPONSE.disclaimer is forced to `AI_DISCLAIMER`; LLM output
  cannot override it.
- Real provider's `_parse_response` rejects any LLM output that
  contains a forbidden phrase, raising `AIProviderError("safety_violation")`.

## On Knowledge Documents

Knowledge documents (`knowledge/`) may describe concepts in detail,
but they must never:
- Cite a specific national or industry standard by its code
  number.
- Provide a specific structural safety limit (e.g. "crack width
  > 0.3 mm requires immediate repair").
- Claim to be the official specification of any external system.

Knowledge documents describe what the BuildHealth prototype **does**,
not what any external authority **requires**.
