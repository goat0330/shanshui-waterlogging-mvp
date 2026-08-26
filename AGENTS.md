# Repository Rules

1. Latest `main` is the only development baseline. Old RC/worker branches are historical evidence only.
2. Shared contracts have one meaning. External source drift is normalized in source adapters; do not loosen internal domain schemas to absorb upstream variants.
3. Generated runtime assets must be fresh after decision/schema changes.
4. Workers own implement → test → repair → retest for their bounded task before creating another repair branch.
5. `docs/06_DELIVERY_MANIFEST.md` is the current-state document. `docs/RC2_SOURCE_PROVENANCE_POLICY.md` is the frozen MVP evidence-gate policy.
6. A task is complete only after the smallest affected end-to-end path passes.

## Frozen MVP evidence gates

Do not reopen the following as blockers unless new contradictory evidence is produced:

- 8 historical public-report cases are `VERIFIED_FOR_MVP`.
- Missing historical media/depth is valid and does not invalidate a case.
- Approved same-event media is `CASE_SOURCE_MEDIA`; do not render or report `权限待用户确认`.
- Local research video is allowed for local MVP when labeled non-live/research. External redistribution/production rights are separate gates.
- Learned water-segmentation candidate is verified for research MVP by the checked-in held-out mask metrics; this does not verify metric centimetre depth.

## worker-ship execution policy

For bounded frontend/backend work, the originating Worker owns latest-main sync, self-review, relevant checks, PR/CI, serialized merge, and confirmation that `origin/main` contains the result. Do not repeatedly ask the user to reconfirm a gate already frozen above.

- “Push to main” means branch push → PR/CI → serialized merge → confirm `origin/main`.
- `contracts/**` remains single-owner Contract/Architect work.
- Dirty historical worktrees are frozen; do not delete them without explicit instruction.
- PostGIS/MQTT/Auth/production hardening must not block the current fixture/API MVP unless the task explicitly targets production readiness.
