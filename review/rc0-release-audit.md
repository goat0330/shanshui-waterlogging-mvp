# RC0 Release / Canonical Audit

## Main Agent independent RC0 update (2026-08-22)

The worker boundary audit below was followed by an independent rerun on the integrated tree:

| Check | Result | Evidence |
|---|---|---|
| Backend memory contract/telemetry | PASS | `python -B backend/smoke.py` |
| VisionDepth baseline | PASS | `python -m vision.smoke`; 3-image baseline, including `NO_REFERENCE` |
| Frontend typecheck/build | PASS | `npm run typecheck`; `npm run build` |
| Fixed 1920×1080 Cesium browser smoke | PASS | `frontend/review/dashboard-cesium-1920x1080.png`; OSM scene source, 30 external Cesium responses HTTP 200 |
| API live/fallback/reconnect | PASS | `review/e2e/api-realtime-browser-smoke.json`; 5s polling observed and stopped after reconnect |
| Geographic Cesium marker/forecast | PASS (technical) | `review/e2e/rc0-cesium-geographic-smoke.json`; NOW/+10/+30 GeoJSON HTTP 200 and ready |
| 60-second core chain | PASS | `review/e2e/60-second-chain.json`; induced network errors are expected during degradation |
| 5-minute rehearsal | PASS | `review/e2e/5-minute-rehearsal.json`; 310.3s, 11 checkpoints, no page/console errors |
| Human visual review | VISUAL_REVIEW | User owns final comparison against `references/golden-dashboard.png` |

The remaining conditional items are deliberate: CCTV is a marked placeholder rather than a real feed, VisionDepth has no calibrated Shanghai CCTV backend adapter, PostGIS live verification is open, and formal survey/building-element coordinate calibration is open. No worker is allowed to present those as closed gates.

审计日期：2026-08-22  
审计范围：仓库边界、首个 commit 的排除项、secret pattern、release 文档和 RC0 gates。  
角色边界：本审计没有修改 frontend/backend/contracts/vision/Cesium 实现，没有删除文件，没有 commit/reset/revert。

## 结论

**Status: `PASS — RC0 TECHNICAL / VISUAL_REVIEW`**

当前工作树在 `main`，canonical commit 为 `9628d21cfccefdfc03cda46e0247aac8c40b79e2`，并已作为 RC0 rollback anchor。本审计与后续 Main Agent 复跑只证明本地技术主链，不把 fixture、截图、build 或文档存在误报为生产交付。

## 1. Git boundary evidence

| Check | Result |
|---|---|
| `git rev-parse --show-toplevel` | `D:/研究生作业/上海城市内涝_智慧平台/git` |
| `git branch --show-current` | `main` |
| `git log --oneline -5` | `No commits yet on main` |
| `git rev-parse --verify HEAD` | failed as expected: `Needed a single revision` |
| `git status --porcelain=v1 -uall` | 148 untracked paths at the initial audit snapshot; the shared parent workspace added further review/API artifacts afterward |
| `git status --ignored --porcelain=v1 -uall` | 45,556 ignored entries at the initial snapshot, dominated by dependencies/runtime tiles |
| `git ls-files --others --exclude-standard` | 148 release candidates at the initial snapshot; later shared-tree probes reported 154 and then 159 as parent artifacts landed, so Main Agent must rerun this immediately before staging |

The first commit must be staged as an explicit release set. `git add .` is unsafe while the tree is uncommitted because it would include local metadata and generated review archives unless the ignore rules or an explicit path allowlist are respected.

## 2. Secret audit (values intentionally omitted)

The bounded scan covered 140 repository text/config files, skipped no file over 5 MiB, and had zero read errors. It found no private-key marker or common provider-token shape in release text. It did find:

- `frontend/.env.local`, one line / 327 bytes, contains a JWT-shaped value assigned to `VITE_CESIUM_ION_TOKEN`. The value was not printed, copied, hashed, or written to any report. It is ignored by `.gitignore:3` (`.env.*`) and appears as `!!` in Git status.
- The ignored generated artifact `frontend/dist/assets/index-bOn-Ja1u.js` also contains a JWT-shaped match from the local build. Only the path and pattern class were recorded; no value was printed or copied. The worker did not delete the artifact. Do not stage or distribute `frontend/dist/**`; rebuild/clean it under the parent agent's release procedure with secret-bearing local env excluded.
- `spikes/cesium/src/main.ts:349` matched a broad secret-assignment pattern, but the redacted structure is an `import.meta.env` reference rather than a literal secret.
- The only environment variable names discovered in env examples/local config are `VITE_CESIUM_ION_TOKEN`, `REPOSITORY_BACKEND`, and `DATABASE_URL`. Runtime code also reads `VITE_DATA_SOURCE`, `VITE_API_BASE_URL`, and `SMOKE_PORT`.

Release action: keep `.env.local` untracked, never paste its value into docs/CI/commit messages, and make any real token rotation decision outside this audit if it has been shared elsewhere.

## 3. First-commit exclusion map

| Path or pattern | Observed size/evidence | RC0 action | Reason |
|---|---:|---|---|
| `data/source/**` | `1,949.34 MiB` total: SKP `1,516.84 MiB` + SHP sidecars `432.50 MiB` | Exclude | Original city-model binaries; not needed to install/run RC0 and already ignored by `data/source/`. |
| `data/runtime/**` | 4,663 files / `652.37 MiB` | Exclude | Generated BimAngle/Cesium runtime data; already ignored by `data/runtime/`. |
| `frontend/public/data/shanghai-core/**` | runtime junction/view into local city tiles | Exclude | Local generated city runtime; already covered by the runtime ignore rules. |
| `spikes/cesium/public/data/tiles/**` | local captured tile tree | Exclude except `shanghai-aoi/manifest.json` | Keep only the small manifest exception; do not stage captured tiles. |
| `frontend/node_modules/**` | 6,655 files / `289.04 MiB` | Exclude | Installed dependency tree; covered by `node_modules/`. |
| `spikes/cesium/node_modules/**` | 4,977 files / `286.67 MiB` | Exclude | Installed dependency tree; covered by `node_modules/`. |
| `frontend/dist/**`, `.vite/`, `__pycache__/`, logs | generated build/cache output; `frontend/dist` was present in the later shared-tree probe | Exclude | Generated output is not source or a rollback artifact; covered by existing ignore rules. |
| `frontend/.env.local` | `327` bytes; JWT-shaped token-like value | Exclude | Local secret-bearing config; covered by `.env.*`. |
| `.codex/**` | 3 local agent prompt files / `6,289` bytes | Exclude | Local orchestration metadata, not application source or release documentation; newly ignored by this audit. |
| `frontend/review/*.zip` | `v0.2` `6.47 MiB`; `v0.3` `6.86 MiB` | Exclude from RC0 | Generated review archives are redundant with selected PNG evidence and newly ignored by this audit. Preserve on disk; force-add only if a later release explicitly requires them. |

Other unignored binary evidence is smaller but must not be bulk-staged without intent: `references/golden-dashboard.png` (`3.36 MiB`), `vision/artifacts/smoke_inputs/dry_street.jpg` (`3.82 MiB`), four `frontend/review/dashboard-*.png` files (`1.75–2.10 MiB` each), and `spikes/cesium/review/l1-shanghai-shader.png` (`1.20 MiB`). They may be release evidence only after the parent confirms provenance and usefulness.

The `.gitignore` change is limited to the two objectively missing release-boundary rules above. No source/runtime asset was removed.

## 4. Stale manifest issues found

`docs/06_DELIVERY_MANIFEST.md` was stale in the following ways and is replaced with an RC0-specific manifest:

- it pointed the primary frontend commands at `spikes/cesium/` instead of `frontend/`;
- canonical branch/commit fields were empty without saying that the repository has no commits;
- API, contract, backend smoke, and integration gates were marked `NOT VERIFIED` despite the current backend memory smoke and frontend typecheck evidence;
- it did not list the current API/fixture environment names or distinguish default fixture mode from API mode;
- it did not classify CCTV placeholder, VisionDepth baseline, PostGIS, range-level versus formal coordinate calibration, or visual review honestly;
- it had an obsolete `LLM API KEY` row even though current RC0 runtime code does not read an LLM key;
- its rollback section was empty.

## 5. RC0 release checklist

### Canonical identity

- [x] Current branch is `main`.
- [x] Main Agent creates the canonical commit after integration: `9628d21cfccefdfc03cda46e0247aac8c40b79e2`.
- [x] Record the resulting commit SHA in `docs/06_DELIVERY_MANIFEST.md` and this audit.
- [x] Record a known-good visual/build artifact tied to that SHA.
- [ ] Before the first commit, inspect `git diff --cached --name-status` and confirm none of the exclusion map is staged.

### Startup commands

- [x] Frontend install/runtime entry is `frontend/`: `npm install`, `npm run typecheck`, `npm run dev`.
- [x] Backend install/runtime entry is `backend/`: `python -m pip install -r requirements.txt`, then `python -m uvicorn app.main:app --reload --port 8000`.
- [x] Backend smoke command is `python -B smoke.py` from `backend/`.
- [x] Parent runs a clean frontend `npm run build` with local secret material excluded from the staged release set.
- [ ] Parent performs the final human fixed 1920×1080 Golden Reference visual review on the integrated tree.

### Environment names (names only; no values in Git)

- `VITE_DATA_SOURCE`: optional; `api` selects REST/WebSocket mode, otherwise fixture mode is used.
- `VITE_API_BASE_URL`: API-mode base URL; code default is local `127.0.0.1:8000`.
- `VITE_CESIUM_ION_TOKEN`: optional for OSM Buildings; local Huangpu fallback does not require it.
- `REPOSITORY_BACKEND`: optional backend selector; default is in-memory fixture-backed repository.
- `DATABASE_URL`: required only when `REPOSITORY_BACKEND=postgres`; do not commit a value.
- `SMOKE_PORT`: optional backend smoke port override.

### Gates

Verified in this audit:

- [x] Repository root/branch/commit absence/ignore boundary inspected.
- [x] Secret-pattern scan completed without emitting values.
- [x] `python -B backend/smoke.py` — `PASS`, including REST, CORS, WebSocket, telemetry projection, simulator, 404/422 boundaries, and memory/migration configuration.
- [x] `npm run typecheck` in `frontend/` — `PASS`.

Conditional or still open:

- [ ] Frontend production build — `NOT VERIFIED` in this audit; intentionally not run because the local token-bearing env could be embedded into generated `dist` output.
- [ ] Local Cesium/Huangpu scene — `CONDITIONAL`; existing screenshots/runtime evidence are not a fresh integrated release gate and runtime tiles remain local/ignored.
- [ ] OSM Buildings — `CONDITIONAL`; requires a separately managed `VITE_CESIUM_ION_TOKEN` and network/access verification.
- [ ] CCTV/video — `NOT VERIFIED`; current `cctv-placeholder.webp`/`DEMO FEED · 场景占位` is a placeholder and not a real camera or MP4/RTSP feed.
- [ ] VisionDepth — `CONDITIONAL` baseline only; local public-image smoke evidence exists, but model weights, Shanghai CCTV generalization, calibrated centimeter accuracy, and backend integration remain `NOT VERIFIED`.
- [ ] PostgreSQL/PostGIS — `CONDITIONAL` / `NOT VERIFIED`; migration/configuration is present, but live migration, seed, restart persistence, spatial query, and PostGIS instance evidence are absent.
- [ ] Formal coordinate calibration — `NOT VERIFIED`; `review/huangpu-range-calibration.md` supports range-level alignment only, not control-point/building-element matching.
- [ ] Visual review — `CONDITIONAL` / `VISUAL_REVIEW`; fixed-size screenshots exist, but final human comparison to the Golden Reference is not a release acceptance result.
- [ ] Five-minute integrated E2E, real device/official API, production deployment, and rollback rehearsal — `NOT VERIFIED`.

### Known deviations

- RC0 uses fixture/demo data by default; it is not official Shanghai realtime data or physical sensor/hardware evidence.
- Analysis/forecast and CCTV/overlay paths remain synthetic/placeholder-backed where the code and review docs say so.
- Runtime city assets and source binaries remain local to the project disk and are intentionally outside the first Git commit.
- There is no previous stable Git commit. The RC0 rollback point and anchor are `9628d21cfccefdfc03cda46e0247aac8c40b79e2`; use a revert-based recovery plan.

## 6. Commands run

```text
git status --short --branch
git rev-parse --show-toplevel
git log --oneline --decorate -5
git status --ignored --short --untracked-files=all
git check-ignore -v -- frontend/.env.local backend/.env.example frontend/.env.example
git ls-files --others --exclude-standard
python -B backend/smoke.py
npm run typecheck                 # from frontend/
```

No command in this audit printed a secret/token value. No implementation file was changed.

## 7. Handoff

`changed_files`:

- `.gitignore` — added only `.codex/` and `frontend/review/*.zip` ignore rules; files remain on disk.
- `docs/06_DELIVERY_MANIFEST.md` — updated RC0 release status/checklist.
- `integration/README.md` — updated integration boundary and open gates.
- `frontend/README.md` — updated runtime modes, env names, and truthful evidence limits.
- `review/rc0-release-audit.md` — this audit.

`next_actions`:

1. Main Agent stages a curated allowlist and checks the cached diff against the exclusion map.
2. Main Agent runs the integrated frontend build/browser review with secret-bearing local env excluded from generated artifacts.
3. Main Agent closes or explicitly carries the conditional gates, creates the canonical commit, fills its SHA and rollback anchor, and independently performs final acceptance.

Diagnostic note: one initial PowerShell generated-output scan was invalid because `$matches` is an automatic variable; it was terminated and replaced with a path-only `rg -l` scan, which produced the `frontend/dist/assets/index-bOn-Ja1u.js` finding above. No implementation change resulted.
