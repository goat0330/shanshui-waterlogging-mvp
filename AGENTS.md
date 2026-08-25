# Repository Rules

1. **Latest `main` is the only development baseline.**
   This closeout starts from `main@53b4830`; after closeout, the latest `main` is the only baseline. Old RC and repair branches are historical only.
2. **Shared contracts have one meaning.**
   Use the backend contract field names directly. Do not invent local business aliases. When a shared field changes, update and validate every affected producer and consumer.
3. **Generated runtime assets must be fresh.**
   If decision logic or a schema changes, regenerate overlays and results before validation. Never validate against stale generated JSON.
4. **Workers repair their own task before creating another repair branch.**
   Prefer implement → test → repair → retest on the same task branch.
5. **`docs/06_DELIVERY_MANIFEST.md` is the only current-state document.**
   RC0, RC11, RC2, and VisionDepth progress documents are historical evidence only and must not be used as shared current-state write points.
6. **A task is complete only after the affected end-to-end path passes.**
   Run the smallest relevant integration smoke before merging to `main`.

## worker-ship execution policy

For bounded frontend/backend work, the originating Worker owns the change through
latest-main sync, self-review, relevant checks, PR/CI, serialized merge, and
confirmation that `origin/main` contains the result. The main controller does not
repeat Worker-local diff review, conflict repair, module tests, or CI debugging.

- “Push to main” means branch push → PR/CI → Merge Queue or recoverable local lease
  → confirm `origin/main`; parallel direct pushes to `main` are not allowed.
- `contracts/**` remains single-owner Contract/Architect work; frontend shared
  types/adapters, generated runtime, and the delivery manifest also have one owner.
- If no main controller is present, designate one existing Worker or CI as the
  release owner for exactly one final cross-module E2E. This is not a second audit.
- Old worktrees are classified as ACTIVE / SHIPPED_CLEAN / MISSING /
  BROKEN_METADATA / STALE_DIRTY. Dirty historical worktrees are frozen. Removal of
  a worktree or branch requires explicit confirmation.

The ownership model in `docs/00_MASTER_BLUEPRINT.md` remains valid for Contract and
product decisions; its Architect/Integration role is not a requirement to re-audit
every Worker after this shipping policy is active.
