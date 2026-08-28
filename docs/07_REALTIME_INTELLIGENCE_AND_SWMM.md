# Realtime Intelligence + Open-Source Hydrodynamic Roadmap

## Runtime path now implemented

```mermaid
flowchart LR
    SEN[Sensor telemetry] --> HIST[Depth history]
    HIST --> RISE[Robust rise-rate estimator]
    SEN --> RISK[RiskAssessmentService]
    RISE --> RISK
    MET[Meteorology / nowcast] --> RISK
    WATER[Shanghai Water health] --> RISK

    RISK --> ANA[Structured risk analysis]
    RISK --> FC[ForecastProvider]
    RISE --> FC
    MET --> FC

    FC --> SCN[Scenario catalog if available]
    FC --> EMP[Empirical baseline fallback]

    RISK --> WS[WebSocket]
    FC --> WS
    ANA --> WS
    WS --> UI[Frontend]
```

The risk index is not a probability. Hard safety rules can raise the minimum risk level. Missing/stale Sensor evidence reduces confidence instead of forcing the risk to NORMAL.

## Forecast provider ladder

```text
SCENARIO_LIBRARY
    ↓ catalog unavailable / poor match
EMPIRICAL_BASELINE
    ↓ no live sensor
SYNTHETIC_FIXTURE
```

The empirical baseline exposes uncertainty and method metadata. It is not described as a calibrated hydrodynamic model.

## Offline open-source physical-model path

```mermaid
flowchart LR
    OSM[OSM] --> ANY[SWMManywhere]
    DEM[Public DEM] --> ANY
    BLD[Public building footprints] --> ANY
    ANY --> INP[Synthetic SWMM .inp]
    INP --> API[swmm_api]
    API --> SWMM[PySWMM batch simulation]
    SWMM --> CAT[forecast-scenarios.json]
    CAT --> LIVE[ScenarioCatalogMatcher]
```

Heavy SWMM tooling remains under `research/swmm` and is not imported by the FastAPI runtime.

## Truth boundary

- SWMManywhere network: `SYNTHETIC_UDM`, not official Shanghai drainage GIS.
- `pipeLoadPercent`: scenario baseline until real pipe-network telemetry/model output replaces it.
- Empirical +10/+30: transparent MVP baseline.
- Scenario-library +10/+30: precomputed physical-model support, quality depends on the synthetic/official model and calibration.
- LLM may explain structured results; it does not calculate risk level, depth, road closure or dispatch.
