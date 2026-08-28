# FP-001 Synthetic Drainage Twin Research

This folder keeps heavy hydrodynamic dependencies outside the runtime backend.

## Stack reused

- SWMManywhere — public geospatial data -> synthetic UDM / SWMM `.inp`
- swmm_api — inspect/manipulate SWMM input/output files
- PySWMM — run SWMM and access hydraulic states from Python

No upstream source code is copied into the Qixiao backend.

## 1. Install research-only dependencies

```bash
python -m venv .venv-swmm
.venv-swmm\Scripts\activate
pip install -r research/swmm/requirements-research.txt
```

## 2. Build the first FP-001 synthetic UDM

```bash
python research/swmm/build_fp001_udm.py
```

The generated network is explicitly:

`SYNTHETIC_UDM / NOT_OFFICIAL_NETWORK / RESEARCH_MVP`

SWMManywhere's minimum config only needs base_dir, project and EPSG:4326 bbox. The default bbox here is approximately a 3 km square around FP-001.

## 3. Inspect the `.inp`

```bash
python research/swmm/inspect_swmm_model.py <model_1.inp>
```

## 4. Bind FP-001 to a synthetic node

```bash
python research/swmm/pick_fp001_node.py <nodes.geojson>
```

Review the selected node manually. Nearest geometry does not prove it represents the actual Shanghai drainage node.

## 5. Run a physical baseline

```bash
python research/swmm/run_pyswmm_baseline.py <model_1.inp> --node-id <NODE_ID>
```

## 6. Scenario catalog contract

The live backend already looks for:

```text
data/runtime/forecast-scenarios.json
```

or `FORECAST_SCENARIO_CATALOG`.

When a valid catalog exists, the forecast chain automatically becomes:

```text
SCENARIO_LIBRARY
    ↓ fallback
EMPIRICAL_BASELINE
    ↓ fallback before telemetry
SYNTHETIC_FIXTURE
```

See `scenario_catalog.schema.json`.

Recommended first scenario dimensions:

- currentDepthCm: 0 / 10 / 20 / 30
- forecastRain30Mm: 0 / 10 / 30 / 60
- pipeLoadPercent or drainage-capacity proxy
- blockage/drainage capacity scenarios
- riseRateCmMin where a consistent initial-state method is available

Do not describe SWMManywhere output as the official Shanghai pipe network. The point of this phase is to establish a reproducible physical scenario library before official network data becomes available.

## 7. Convert reviewed runs into the live scenario catalog

After you have a reviewed batch summary CSV with at least:

```text
scenarioId,currentDepthCm,riseRateCmMin,forecastRain30Mm,pipeLoadPercent,nowCm,plus10Cm,plus30Cm
```

convert it with:

```bash
python research/swmm/build_scenario_catalog.py research/swmm/runtime/scenario-summary.csv
```

This writes `data/runtime/forecast-scenarios.json`, which the backend discovers automatically. Do not populate the CSV with empirical/fixture numbers and call it physics-backed; only reviewed SWMM/PySWMM results should be promoted into this catalog.
