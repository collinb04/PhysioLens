Backend/
├── main.py                  # FastAPI app entrypoint / CORS 
├── app/
│   ├── api/                 # HTTP / contract layer
│   │   ├── routes_health.py # Exposes read-only endpoints to run the analytics pipeline and return validated summary and time-series outputs.
│   │   └── schemas.py       # Defines the data contracts for your API.
│   │
│   ├── domain/              # Core business objects & configuration constants
│   │   ├── config.py
│   │   └── daily_record.py
│   │
│   ├── services/            # Application logic
│   │   ├── analytics/       # Recovery attribution engine
│   │   │   ├── baselines.py # Establishes rolling baseline metrics
│   │   │   ├── dips.py      # Identifies meaningful recovery degradations
│   │   │   ├── stability.py # Quantifies each factors volatility over time.
│   │   │   ├── evidence.py  # Scores how strongly each factor explains recovery dips.
│   │   │   ├── pareto_calculation.py # Applies Pareto’s concept of ranking to attribution results.
│   │   │   ├── insights.py  # Transforms analytics into human-readable insight.
│   │   │   └── pipeline.py  # Orchestrates the entire analytics workflow.
│   │   └── ingest/          # Data ingestion layer
│   │
│   ├── tests/
│       ├──  run_pipeline_tests.py
│       ├── stability.py # Quantifies each factors volatility over time.
│       ├── stability.py # Quantifies each factors volatility over time.
│ 
├── data/                     # Seed / demo datasets
│   ├── generate_seed_data.py # Generates random data sets for specfic demo types
│   ├── seed_exercise1.json
│   ├── seed_sleep1.json
│   └── seed_stable1.json
│
└── venv/

