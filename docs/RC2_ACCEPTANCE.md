# RC2 Acceptance Matrix

Status is maintained by Main after independent reruns. Worker self-reports are evidence, not final acceptance.

## Regression

- [ ] Backend compile/smoke
- [ ] Frontend typecheck/build
- [ ] Vision image smoke
- [ ] Real video smoke: 4+ usable MP4
- [ ] API mode browser chain
- [ ] WebSocket fallback/reconnect
- [ ] Cesium geographic scene and orbit/zoom
- [ ] NOW/+10/+30
- [ ] 60-second chain

## Evidence and provenance

- [ ] Upload response contains the approved provenance object
- [ ] URL safety: scheme, timeout, MIME, size, redirect and private-target guards
- [ ] Vision does not overwrite SensorState/FloodPoint current depth
- [ ] Video frame JSON, mask, timestamp and overlay metadata are readable
- [ ] Source manifest records URL/project/license/runtime policy
- [ ] Pending-license binaries and weights are absent from Git

## Dashboard

- [ ] `SENSOR`, `VISION_IMAGE`, `VISION_VIDEO`, `FORECAST` labels are readable
- [ ] Current measured, visual estimate and future forecast remain distinct
- [ ] No fake LIVE claim or meaningless cloud/duplicate business overlay
- [ ] 1920×1080 default/high-risk/+30/gallery states have no critical overflow

## Scenarios and release

- [ ] Scenario A Sensor-driven
- [ ] Scenario B Vision-driven
- [ ] 5-minute rehearsal
- [ ] README, AGENTS, Delivery Manifest, source manifest/download instructions
- [ ] Git clean and no secrets
- [ ] `rc2-evidence-demo` tag

Allowed final status:

```text
PASS / RC2 EVIDENCE-BACKED DEMO / VISUAL_REVIEW
CONDITIONAL / RC2
BLOCKED
```
