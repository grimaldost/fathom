# premortem-ablation-v1 — the matrix run again, and it did not replicate

- **Date:** run 2026-09-19, 19:09–20:41; reported 2026-09-26.
- **Gate:** keel's **KEEL-B09**, the same as the first matrix
  (`docs/reports/2026-08-11-premortem-ablation-v1-first-matrix.md`).
- **Verdict: the first matrix's headline does not hold.** Run a second time with the same arms,
  specs, model id and configuration, the ~225-word core no longer matches the full directive on
  the two citation-grounding criteria: 2 of 6 against 6 of 6. The structural half of the gate is
  open again, not settled.

## Why it was run a second time

The first matrix's report said the finding-lists for the blinded human pass "now exist in the
workspaces". They did not. Each trial stages into a temporary workspace that the run removes when
the trial ends (`taskbank.stage_task`, a `finally` around `mkdtemp`), the ledger keeps the
verifier's booleans and the economy fields but not the text, and raw stream capture was opt-in and
was not switched on for that run. The lists were gone as each trial finished, so the pass the
report named as the one that settles the gate could not be run on them.

The second run is the same matrix with the raw stream kept (`FATHOM_STREAM_DIR`, which since the
T35a change is also the default for every arm of this bank). A one-trial pilot proved the
reviewer's `Write` of `findings.md` comes back whole from the stream before the other seventeen
were bought. The eighteen lists, their streams and the run log are kept outside this repository;
the run's own ledger is committed beside this report (below).

## What is the same

| | 2026-08-11 | 2026-09-19 |
|---|---|---|
| arms | `arm-a-full`, `arm-b-core`, `bare` | same scenario files |
| specs | 6 dev specs, holdout sealed | same, holdout still sealed |
| repeats | 1 | 1 |
| model id | `claude-opus-4-8`, strong | same, on all 18 runs |
| `config_hash` per arm | `40a6afc0…`, `b204c376…`, `d655fa66…` | identical |
| cost | $20.13 | $23.13 (a-full $8.21, b-core $7.43, bare $7.48) |

## What changed

Trials passing each criterion, of 6 per arm:

| criterion | 08-11 full | 08-11 core | 09-19 full | 09-19 core | 09-19 bare |
|---|---:|---:|---:|---:|---:|
| `citations_line_in_range` | 6 | 6 | 6 | **2** | 0 |
| `citations_path_exists` | 6 | 6 | 6 | **2** | 0 |
| `every_finding_cites_evidence` | 6 | 6 | 6 | 5 | 0 |
| `unverified_offline_line` | 6 | 0 | **4** | 0 | 0 |
| the other eight criteria | same | same | same | same | same |

The first report's claim was that the core ties the full body on nine of twelve criteria
"including both citation-grounding checks", and that is what licensed the compression. On this run
the core keeps every shape criterion and loses the grounding of its citations in four trials of six
— the property a pre-mortem's findings are worth reading for.

## What it means

Two explanations fit, and this run cannot choose between them:

1. **The served model moved under a pinned id.** Same id, five weeks apart.
2. **One repeat per cell never supported the conclusion.** The first report said so in its own
   caveats ("every observed cell is 6/6 or 0/6 with no variance at all … a criterion that is
   *nearly* saturated would be indistinguishable from one that is fully saturated at this power"),
   but its verdict line did not carry the caveat, and neither did the rows that cited it.

Either way, KEEL-B09's structural half is not settled, and no directive text should be retired on
it. The blinded human pass is now possible — the lists exist — and is deferred to a later round
together with the question of whether to buy repeats (three per cell is about $45 at this run's
rate) to separate noise from a moved model.

## Ledger

`docs/reports/2026-09-19-premortem-ablation-v1-replication.ledger.jsonl`: 36 rows, 18 runs and 18
completed trials, written by `fathom run premortem-ablation-v1 --scenarios-dir
scenarios/premortem-ablation --repeats 1` into a separate ledger directory. It is kept here rather
than appended to `ledger/premortem-ablation-v1.jsonl` on purpose: the two runs record the same
`(dataset_version, config_hash, task, repeat)` cells, and two completed lines for one cell are what
`fathom report` warns about and double-counts in Economy. Neither run is invalid, so neither belongs
in `ledger/archive/`; the canonical ledger stays the first run's, and this file is its replication.
