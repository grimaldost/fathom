# Ledger index — the stamp every verdict is read against

**Generated. Do not hand-edit.** Re-render with `python tools/ledger_index.py --write`;
`tests/test_ledger_coverage.py` fails while this file and `ledger/` disagree.

One row per committed ledger (archived ledgers under `ledger/archive/` are excluded, per
the coverage ratchet). `n by arm` counts trial rows with `status == "completed"` only —
the same rule the resume key and every scorecard use, so an errored trial is never a
measured failure. A document that quotes a per-arm n, a pooled control total or a p-value
for one of these banks is quoting *this* row; if it disagrees, the document is stale.

| Bank | ledger sha256 | n by arm (completed) | trial rows | run rows |
|---|---|---|---|---|
| `ablation-v1` | `12bd4036ba70da1544af396f4b9e26f02fc581a5150983272443c56b82e252f3` | bare-sonnet5:5 | 5 | 5 |
| `ablation-v2` | `157d38e2814b4c8f52269497a52ee520eed1a738428d5692dede6beba9f65ed7` | bare:17, bare-authoring:8, bare-gate:17, bare-gate-review:5, bare-reprompt:8, haiku:8, haiku-authoring:10, haiku-gate:8, haiku-gate-review:10, haiku-gate-sg:10, haiku-reprompt:8, lazy-gate:2, opus:8, orchestrated:17, sonnet-lo:8, sonnet-lo-gate:8 | 228 | 371 |
| `context-size-v1` | `5312c95c4552d93da59689ebb7b18547af0ca127c489904e1702a3d0475bd79f` | haiku:40, opus:20 | 60 | 60 |
| `dc-consumers-v1` | `4d4c36f0c19139ce33e0762afdaeac85c5f84e9b0ef5509ea46cb6dc3077332d` | product-haiku:30, product-sonnet:30 | 60 | 60 |
| `dc-granularity-v1` | `d56b9fbbebd46c98b542a61831938e5e9a853bac8084c3486543bdb9e88504e8` | coarse-sonnet:9, fine-sonnet:9 | 18 | 18 |
| `dc-stack-v1` | `09b2d484ad6deda4c6583269519edd89147ff26778d254b1f5db0769a8480673` | stack-sonnet:12 | 16 | 16 |
| `e1-data` | `9aedcf67cbef205f4d8836a9ca1988303b49e8a2de283a38650bc56c9553e84d` | e1-data-bare-haiku:2, e1-data-bare-sonnet:2, e1-data-classifier-haiku:2, e1-data-classifier-sonnet:2, e1-data-oracle-haiku:2, e1-data-oracle-sonnet:2, e1-data-registry-haiku:2, e1-data-registry-sonnet:2 | 16 | 16 |
| `e1-debug` | `18a2c6b2397856b42e3fc5a6033e92c65f4ed69538679ba467d9ba277dfba5ce` | e1-debug-bare-haiku:2, e1-debug-bare-sonnet:2, e1-debug-classifier-haiku:2, e1-debug-classifier-sonnet:2, e1-debug-oracle-haiku:2, e1-debug-oracle-sonnet:2, e1-debug-registry-haiku:2, e1-debug-registry-sonnet:2 | 16 | 16 |
| `e1-verif` | `e9b4fc5923d5b3f5f5e922409be9b0ae1ca124501bec50c9418c2d968161dc3d` | e1-verif-bare-haiku:2, e1-verif-bare-sonnet:2, e1-verif-classifier-haiku:2, e1-verif-classifier-sonnet:2, e1-verif-oracle-haiku:2, e1-verif-oracle-sonnet:2, e1-verif-registry-haiku:2, e1-verif-registry-sonnet:2 | 16 | 16 |
| `humble-vs-super-v1` | `48df02e8415227a92de0e57a8f216ebf538014824c50bd83c91db1ea0356aeab` | bare:20, humble-only:30, stack-humble:30, stack-super:20, super-only:20 | 120 | 120 |
| `humble-vs-super-v2` | `2fe9e40536cac63bdc28bbffa174ddd236aeb3b72f23c0bf47cfd553a7bb2127` | stack-humble:20, stack-super:20, super-only:20 | 60 | 60 |
| `humble-vs-super-v3` | `efb00e24dc27973b1cd8bfff5b7f66eeeb030614cab737ca357299346179f823` | bare:45, stack-humble:45, stack-super:45, super-only:45 | 180 | 180 |
| `humble-vs-super-v4` | `014bca37168b3c5bcd514820c1b3e9cd28d38e4331c9716391fdc966dafa7d48` | bare:8, stack-super:8 | 16 | 16 |
| `inject-content-v1` | `ab76c68247c94e7be2fb7a5803f141102a35e221680840488f608a46ca21ca29` | bare:10, nudge:10, protocol:10 | 30 | 30 |
| `model-tier-effort` | `f76b52e777a473e7d1b041aa147c192b52ca585be33f3ca216715e7d0fd3f39b` | haiku-xhigh:5, sonnet-xhigh:5 | 10 | 10 |
| `model-tier-v1` | `7cd5f4fcdb2b62da2e1b2c14decf86d87a7867c9491eea70ab0b81421c0198f5` | haiku:35, opus:35, opus5:35, sonnet:35, sonnet5:35 | 175 | 175 |
| `premortem-ablation-v1` | `3dba0503c78f49ec8170e7b00b8dd3da013d69ba4cf2d333c3178435ec120d21` | arm-a-full:6, arm-b-core:6, bare:6 | 18 | 18 |
| `skill-pyeng-v1` | `3409b2cb89ba14949d45bcf2b88df3ef2e080eced4bd4db7d1c191d708916c88` | bare:4, generic-nudge:4, pyeng-skill:6 | 17 | 17 |
| `tu-grounding-e2e-v1` | `0afef71ae5de90cd8455da38d96d3775a716c53ce63b08ef91760acadf2914b5` | control-haiku:3, control-opus:3, control-sonnet:3, drift-sonnet:3, treatment-haiku:3, treatment-opus:3, treatment-sonnet:3 | 21 | 21 |
| `tu-grounding-v1` | `59ffe9c7330a44439653770c6e28155793dd0bca5712e5bc2796d72f3958c7b9` | armed-haiku:3, armed-opus:2, armed-sonnet:3, bare-haiku:3, bare-opus:3, bare-sonnet:3 | 27 | 27 |
