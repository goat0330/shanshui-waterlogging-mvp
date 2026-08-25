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
