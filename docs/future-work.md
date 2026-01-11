# Future Work & Design Extensions

This document outlines potential extensions to PhysioLens if developed beyond a hackathon scope. The focus is on improving correctness, interpretability, and real-world applicability rather than adding surface-level features.

---

## Real-World Data Ingestion

- Integrate real data ingestion APIs for wearables and nutrition tracking.
- Data would be normalized into a unified daily schema, validated for gaps and latency, and aligned via timestamps to support cross-factor analysis.

---

## Causal Assumptions and Factor Interactions

- Expand causal analysis and interaction modeling between factors.
- Intuitively, this model is easy to critique if its assumptions are not made explicit.

- Each behavioral factor (sleep, exercise, nutrition) is measured independently relative to baseline. This is a deliberate simplification rather than a causal claim. In reality, these factors are highly co-dependent: changes in exercise are often driven by prior sleep or nutrition, and their physiological effects interact.

- For example, reduced exercise may correlate with improved short-term recovery if sleep or nutrition improves, but this does not imply that exercising less is beneficial for overall health. Long-term outcomes such as VO₂ max, which are strongly influenced by sustained exercise, are not directly optimized by this model.

- Accordingly, the model is best interpreted as identifying short-term recovery deviations, not prescribing optimal health behaviors or causal interventions.

- With more time, I would expand the model to better capture cross-factor interactions and longer-term effects while maintaining clear separation between analysis and recommendation.

---

## Recovery Signal Quality

- Hone an accurate recovery indicator.
- Ideally, recovery values would be externally computed (e.g., from wearables or composite scoring systems) and analyzed as-is without reinterpretation.

---

## Natural Language Explanations

- Improve natural-language explanations of metrics and insights.

---

## Product Surface and Onboarding

- Add a full landing page and onboarding flows.
- For professionalism, resource access, and a larger brand.

---

## Infrastructure and Persistence

- Replace the seed-based data store with a production database.
- The current seed-based data store is used to enable rapid iteration and deterministic testing, but it does not support persistence, concurrency, or scale.
- Replacing it with a production database (e.g., Postgres) would allow reliable storage of longitudinal user data, transactional integrity, and efficient time-series queries, which are required for real-world ingestion, multi-user support, and historical analysis.

---

## Longitudinal Learning

- Implement longitudinal learning across extended time horizons.
- Extend the system to learn from user data across longer time horizons by modeling trends, seasonality, and delayed effects between behaviors and recovery.
- This would enable adaptive baselines and more stable signal detection as user physiology evolves over weeks and months, reducing sensitivity to short-term noise while better reflecting long-term health changes.

---

## Clinical and Educational Context

- Incorporate clinician-reviewed educational resources.
- Explaining what to target for the most efficient results is only a single piece of the puzzle.
- Ideally, PhysioLens would not only provide the *what*, but the *how*, and eventually the *when*.
- The current focus would not be to give advice, but to provide users with accurate and clinician-reviewed studies to make informed decisions about their health.
