# Examples

| Directory | What it is |
|---|---|
| [`data-root/`](data-root/) | A complete, minimal data root: one bank with one task, a control and a treatment arm, a small synthetic ledger, the generated ledger index and a status page. Its [README](data-root/README.md) walks through it file by file. |

The example is the reference for the layout the engine expects. It is also what the engine's
tests and CI run against: `uv run fathom --home examples/data-root reconcile` is one of the
gates in [`CONTRIBUTING.md`](../CONTRIBUTING.md#gates), and a pre-commit check re-derives its
arms' config hashes to confirm the ledger rows still match the scenario files. Change it with
the same care as any data root: its ledger is append-only, and editing
`scenarios/assets/nudge.md` or an arm's settings would change that arm's hash.

To build your own bank, start with `fathom init` and follow the authoring guide,
[`skills/fathom-eval/reference/authoring.md`](../skills/fathom-eval/reference/authoring.md),
using `data-root/` as a model. Keep your data root in its own repository, not in a copy of
the engine.

Free commands to try against the example, from the engine repository root:

```sh
uv run fathom --home examples/data-root validate example
uv run fathom --home examples/data-root run example --dry-run
uv run fathom --home examples/data-root report example
uv run fathom --home examples/data-root index
uv run fathom --home examples/data-root reconcile
```

None of them spawns a model or spends anything. `report` writes
`examples/data-root/report/scorecard-example.md`, which is not committed.
