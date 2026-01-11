# PhysioLens

## Demo Presentation Link


## Project Overview

PhysioLens is a personal health analytics web application designed to consolidate multiple user-selected data sources such as, sleep, exercise, and nutrition—into a single, interpretable view of recovery. Rather than distributing attention evenly across all inputs, PhysioLens surfaces the single factor most responsible for recovery instability in the current window.

The system is inspired by **Pareto’s Law**, the idea that a small number of inputs often explain a disproportionate share of outcomes. By quantifying how strongly each factor is associated with recovery dips, PhysioLens helps users prioritize stabilization of the factor most likely to yield the greatest improvement, rather than spreading attention evenly across all inputs.

PhysioLens intentionally emphasizes **explainable, per-user analysis** over black-box prediction. All outputs are derived from transparent statistical methods and are traceable back to the underlying data.

## Why PhysioLens

Most health dashboards overwhelm users with metrics. PhysioLens reduces complexity by identifying which factor matters *most right now*, enabling focused intervention instead of diffuse optimization.

---

## Core Concepts

- **Recovery**  
  A composite physiological readiness signal treated strictly as an analytical input, not a diagnosis or predicted outcome.

  PhysioLens does not attempt to predict recovery. Instead, recovery is ingested as a time-series signal, and the system analyzes how other factors (sleep, exercise, nutrition) are associated with meaningful deviations that have already occurred.


- **Baseline (personal, rolling)**  
  A rolling, user-specific reference range computed from recent historical data. All deviations are evaluated relative to the individual’s own baseline rather than population averages.

- **Factor Attribution**  
  A method for estimating how strongly each factor (sleep, exercise, nutrition) is associated with observed recovery dips within a given window.

- **Dip (large vs. persistent)**  
  A dip is a day where recovery falls meaningfully below baseline. If a dip is both large and persistent, the large classification takes precedence.

  - *Large dips* represent high-magnitude deviations.  
  - *Persistent dips* represent sustained deviations across consecutive days These dips are less magnifying, thus carry less weight.

- **Signal Strength**  
  A qualitative measure of how consistently and strongly an association appears given the available data, accounting for magnitude, frequency, and data sufficiency. Signal strength reflects confidence in the association, not causality.

---

## High-Level System Flow

1. Load user time-series data  
2. Compute per-metric personal baselines  
3. Detect recovery dips relative to baseline  
4. Attribute dips to associated factors using standardized deviations  
5. Aggregate attribution using Pareto-style weighting  
   (emphasizing factors that explain the majority of observed deviation)
6. Generate insight text and signal strength indicators  

---

## System Architecture

- Frontend (Vue.js/Nuxt): visualization of recovery trends, factor attribution, and insights  
- Backend (Python FastAPI): data ingestion, analytics pipeline, API endpoints  
- Analytics Engine: baseline modeling, dip detection, factor attribution  
- LLM Layer: generates educational, non-diagnostic explanations based on dominant factors

---

## What it looks like
![Sleep associated factor demo scenario insights](docs/images/SleepInsights.png)
![Sleep associated factor demo scenario graph and metrics](docs/images/SleepChart.png)

## Demo Scenarios

The application includes three controlled demo datasets to validate expected system behavior:

- **Stable Scenario**  
  Minimal recovery dips and no dominant factor attribution in the first month. Used to demonstrate baseline stability and low signal strength.

- **Exercise-Driven Dips**  
  Recovery dips primarily associated with elevated exercise load. The system should attribute the majority of dip explanations to exercise.

- **Sleep-Driven Dips**  
  Recovery dips primarily associated with sleep variability or insufficiency. The system should attribute the majority of dip explanations to sleep.

These scenarios allow reviewers to verify that outputs change meaningfully based on underlying data patterns rather than hard-coded assumptions.

### Generating new scenarios
## DISCLAIMER: This will overwrite existing scenarios

```bash
cd Backend
python ./data/generate_seed_data.py
```

## Default Demo User IDs
    stable1
    exercise1
    sleep1

---

## AI & ML Approach

The core analytics pipeline is intentionally **deterministic, explainable, and auditable**. The system uses classical applied machine learning techniques, including personalized baseline modeling, anomaly detection via standardized deviations, temporal persistence analysis, and attribution under uncertainty.

A large language model (LLM) is layered on top of the analytics to provide **general educational resources** relevant to the detected dominant factor. The LLM does not perform health analysis, make predictions, or generate conclusions.

---

## Responsible AI & Limitations

- Association does not imply causation  
- Factor attribution may be influenced by confounding interactions (e.g., exercise, sleep, and nutrition are interdependent)  
- Analysis is limited by available data windows and metric completeness  
- The system does not provide medical advice, diagnosis, or treatment  
- Demo scenarios are synthetic and intended for validation purposes  

---

## API Overview

- `GET /health/summary`  
  Returns recovery statistics, dominant factor attribution, signal strength, and insight text for a given user and window.

- `GET /health/timeseries`  
  Returns daily time-series data with dip annotations and per-day factor deviations.

---

## Running the Project Locally

### Backend Setup
```bash
cd Backend
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Frontend Setup
```bash
cd Frontend
npm install
npm run dev
```

---

## Testing & Validation

Validation focuses on correctness and reliability rather than exhaustive coverage:
- Unit tests for core math and logic (baselines, z-scores, dip detection)
- Scenario checks to ensure the dominant factor matches each demo dataset
- Deterministic outputs so results are reproducible across runs


