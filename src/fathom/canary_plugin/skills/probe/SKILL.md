---
name: probe
description: "Canary skill for the fathom smoke mount/available gate (ADR-0006). Never triggered in production — its presence in the spawn's init-event `skills` list proves `--plugin-dir` wiring reaches the live CLI."
---

# Mount probe (fathom canary)

Canary skill for the fathom smoke mount/available gate. Never triggered in
production — its presence in the spawn's init-event `skills` list is the
signal that proves `--plugin-dir` wiring reaches the live CLI.
