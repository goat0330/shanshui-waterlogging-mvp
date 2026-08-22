# RC2 Backend Evidence API

状态：`CONDITIONAL`。

## Audit

- Worker worktree：`worktrees/backend-rc11`。
- Branch：`worker/rc11-backend`。
- Worker HEAD：`a6d9d0402c931c5c09d4db7706f852b066e7f981`。
- Main baseline：`5954570`。
- Main 已包含当前 worker 的 RC1 ancestor，并另外包含 frontend/media/`backend/visiondepth_v2` 等其他 worker-owned 改动；本轮未触碰这些范围。

## P0 status

- 既有 upload/url endpoint、VisionDepthAdapter 和 Telemetry/WS/Forecast/Analysis regression 保持可复用。
- 当前 frozen Contract 不包含 RC2 要求的 provenance public fields；详细差异见 `RC2_CONTRACT_PROPOSAL.md`。
- 在不改 Contract 的前提下，已补 URL HTTP/HTTPS、timeout、MIME/size/HTML/SVG、逐跳 redirect 和 private-target/SSRF 边界；URL fetch 关闭环境代理。
- Vision 结果继续只作为 evidence，不写 `SensorState`、`FloodPoint.currentDepthCm` 或 telemetry projection。

## RC2 commands and results

```text
python -m compileall -q app tools                 PASS
python -B smoke.py                                PASS
git diff --check                                  PASS
git status --short --branch                       PASS (after commit expected clean)
```

Smoke 实测：upload 200、private URL 400、invalid URL 400、upload MIME 415、upload size 413、HTML/SVG/unavailable/redirect guard、request JSON error、轻量并发、sensor-vs-vision ownership，以及既有 REST/WS/telemetry/forecast/analysis 全部通过。

## NOT VERIFIED / blockers

- RC2 provenance response cannot be public-implemented until Main/Architect updates frozen `contracts/**`.
- 本轮使用受控 loopback fixture 直接验证 adapter URL media path；由于 SSRF policy 会拒绝 loopback，公网/global URL 的 endpoint 200 尚未在本机 smoke 中实测。
- `backend/visiondepth_v2` video seam is worker-owned and not modified here.
- PostgreSQL/PostGIS, Docker, real hardware, production model, license approval, external services and production deployment remain `NOT VERIFIED`.
