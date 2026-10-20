# Selective experimental provenance

Reviewed source: https://github.com/tjdgus200/openpilot
branch codex/jetson-review, commit a890f6df1bd3eb0478754c68d8b5f92f15e8b722.
Inference commit parent de75c056712fbe19943892919f19960f3e6d565b;
base carrot-nav 74955c98560435895df28a8ae6f9af4d3d414d5f.

The external UPSTREAM.md credits GPU recurrence/reply-event and native AIO design
to zoompilot/jetlink d26001b4161f33bab28d806de6a99b96325a429b under MIT.
Our inspected source is a890f6df, not a claim of equivalence with that upstream
commit. Original Jetlink MIT notice is preserved in LICENSE.

Only reviewed parts are adapted: GPU recurrence controller and finite-scan
source, exact uint8/binary16 LUT conversion, and an isolated bounded AIO writer.
Our changes retain all-state CPU validation, defer D2D commit until validation,
strengthen binding/ownership/cleanup gates and restrict input staging to the
verified Cinque V3 contract. They are not byte-for-byte upstream modules.

No Wi-Fi/HUD/credentials/power/deployment code is imported. No automatic startup
or production default is changed. Device and fastpath overlays require an
explicit experimental candidate build and independently default-off runtime
flags. AIO is not wired into any generated production transport or daemon.

See docs/JETSON_REVIEW_A890_ANALYSIS.md and
artifacts/jetson_review_a890_sources.json for source hashes, findings, tests and
hardware limitations. CPU_FAKE/FIXTURE results do not validate CUDA or USB.
