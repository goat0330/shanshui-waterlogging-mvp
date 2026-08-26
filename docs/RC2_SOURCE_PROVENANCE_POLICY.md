# RC2.3 MVP Evidence Policy — FROZEN

This file is the project truth for MVP evidence gates. Do not reopen a resolved MVP gate merely because production or redistribution remains unverified.

## Formal events

- Exactly **9 formal cards**: `1 REALTIME_EVENT + 8 HISTORICAL_PUBLIC_REPORT`.
- The eight historical cases are **VERIFIED_FOR_MVP** public/official-report cases.
- Historical cases never inherit current `SensorState`, Forecast, or LIVE CCTV.
- Missing official depth is valid and remains `null`.
- Missing case media does not invalidate a historical case.

## Historical media

- Same-event official/public source media approved for this project is `CASE_SOURCE_MEDIA`.
- `mvpUseStatus=APPROVED_LOCAL_MVP` is a project-use gate, not a blanket copyright/redistribution statement.
- UI must not show `权限待用户确认` for these approved MVP bindings.

## Research video

Local research videos may run under:

```text
research_mvp=true
production=false
redistribution=false
mvp_use_scope=local_research_only
```

A pending external redistribution review does **not** block local MVP execution. Research video must be labeled non-live/research video and must never be presented as Shanghai LIVE CCTV.

## Vision image / segmentation

The checked-in evaluation evidence for `Urban Flood Image Dataset` is valid research-MVP evidence:

```text
candidate: pixel_logistic_regression
WebCOOS holdout IoU: 0.648314
OpenCV baseline IoU: 0.395276
```

This verifies the learned **water-segmentation candidate**, not metric centimetre depth, Shanghai production generalization, or live-camera calibration.

## True NOT_VERIFIED boundaries

- calibrated metric centimetre Vision depth;
- real Shanghai LIVE CCTV;
- production deployment;
- public redistribution where separately required;
- CMA warning/radar source until a verified machine-readable endpoint is configured;
- PostGIS/MQTT/Auth production hardening.

## UI policy

Business surfaces show the conclusion and source category. `licenseReview`, calibration, `qualityFlags`, and research-policy detail belong in collapsed technical details and must not be promoted into unresolved product warnings when the relevant MVP gate above is satisfied.
