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
| `ablation-v2` | `398cca699a97fa0a19d14136fbcd51c7f6698e940421bfd49ecc75f8d3914eaa` | bare:17, bare-authoring:8, bare-gate:17, bare-gate-review:5, bare-reprompt:8, haiku:8, haiku-authoring:10, haiku-convoy-gate:8, haiku-convoy-gate-self:8, haiku-gate:8, haiku-gate-review:10, haiku-gate-sg:10, haiku-gate-sg2:8, haiku-reprompt:8, lazy-gate:2, opus:8, orchestrated:17, sonnet-lo:8, sonnet-lo-gate:8 | 252 | 401 |
| `context-size-v1` | `5312c95c4552d93da59689ebb7b18547af0ca127c489904e1702a3d0475bd79f` | haiku:40, opus:20 | 60 | 60 |
| `dc-consumers-v1` | `4d4c36f0c19139ce33e0762afdaeac85c5f84e9b0ef5509ea46cb6dc3077332d` | product-haiku:30, product-sonnet:30 | 60 | 60 |
| `dc-granularity-v1` | `d56b9fbbebd46c98b542a61831938e5e9a853bac8084c3486543bdb9e88504e8` | coarse-sonnet:9, fine-sonnet:9 | 18 | 18 |
| `dc-stack-v1` | `09b2d484ad6deda4c6583269519edd89147ff26778d254b1f5db0769a8480673` | stack-sonnet:12 | 16 | 16 |
| `e1-data` | `9aedcf67cbef205f4d8836a9ca1988303b49e8a2de283a38650bc56c9553e84d` | e1-data-bare-haiku:2, e1-data-bare-sonnet:2, e1-data-classifier-haiku:2, e1-data-classifier-sonnet:2, e1-data-oracle-haiku:2, e1-data-oracle-sonnet:2, e1-data-registry-haiku:2, e1-data-registry-sonnet:2 | 16 | 16 |
| `e1-debug` | `18a2c6b2397856b42e3fc5a6033e92c65f4ed69538679ba467d9ba277dfba5ce` | e1-debug-bare-haiku:2, e1-debug-bare-sonnet:2, e1-debug-classifier-haiku:2, e1-debug-classifier-sonnet:2, e1-debug-oracle-haiku:2, e1-debug-oracle-sonnet:2, e1-debug-registry-haiku:2, e1-debug-registry-sonnet:2 | 16 | 16 |
| `e1-verif` | `e9b4fc5923d5b3f5f5e922409be9b0ae1ca124501bec50c9418c2d968161dc3d` | e1-verif-bare-haiku:2, e1-verif-bare-sonnet:2, e1-verif-classifier-haiku:2, e1-verif-classifier-sonnet:2, e1-verif-oracle-haiku:2, e1-verif-oracle-sonnet:2, e1-verif-registry-haiku:2, e1-verif-registry-sonnet:2 | 16 | 16 |
| `e2-data-semantics` | `a136f06dc20c82adeae4de01c55dcac04b2d3ed40a3150c0fb5b6f98f67aad6e` | bare:6, skill-current:6, skill-vnext:6 | 18 | 18 |
| `humble-vs-super-v1` | `48df02e8415227a92de0e57a8f216ebf538014824c50bd83c91db1ea0356aeab` | bare:20, humble-only:30, stack-humble:30, stack-super:20, super-only:20 | 120 | 120 |
| `humble-vs-super-v2` | `2fe9e40536cac63bdc28bbffa174ddd236aeb3b72f23c0bf47cfd553a7bb2127` | stack-humble:20, stack-super:20, super-only:20 | 60 | 60 |
| `humble-vs-super-v3` | `efb00e24dc27973b1cd8bfff5b7f66eeeb030614cab737ca357299346179f823` | bare:45, stack-humble:45, stack-super:45, super-only:45 | 180 | 180 |
| `humble-vs-super-v4` | `014bca37168b3c5bcd514820c1b3e9cd28d38e4331c9716391fdc966dafa7d48` | bare:8, stack-super:8 | 16 | 16 |
| `inject-content-v1` | `ab76c68247c94e7be2fb7a5803f141102a35e221680840488f608a46ca21ca29` | bare:10, nudge:10, protocol:10 | 30 | 30 |
| `keel-kit-ablation-v1` | `f67492505b6a8fbb36594fcd276249850925cc51ba5c181fe3bcef8bd2d4c2ee` | a-full-014:6, b-vnext-full:6, c-vnext-core:6, d-bare:6 | 24 | 24 |
| `model-tier-effort` | `f76b52e777a473e7d1b041aa147c192b52ca585be33f3ca216715e7d0fd3f39b` | haiku-xhigh:5, sonnet-xhigh:5 | 10 | 10 |
| `model-tier-v1` | `7cd5f4fcdb2b62da2e1b2c14decf86d87a7867c9491eea70ab0b81421c0198f5` | haiku:35, opus:35, opus5:35, sonnet:35, sonnet5:35 | 175 | 175 |
| `model-tier-v2` | `040a9f8a1b9a218cf107dd1b140dc9923318787ef3ef10f2c0d892067febba33` | haiku:33, opus5:33, sonnet5:23 | 89 | 89 |
| `multiagent-composition` | `6eb7a92669400f4038498a6cc6444032480a50a5bb50a3627757a55de128491a` | control-haiku:3, control-sonnet:3, final-haiku:3, final-sonnet:3, perpr-haiku:3, perpr-sonnet:3, placebo-haiku:3, placebo-sonnet:3 | 24 | 24 |
| `premortem-ablation-v1` | `3dba0503c78f49ec8170e7b00b8dd3da013d69ba4cf2d333c3178435ec120d21` | arm-a-full:6, arm-b-core:6, bare:6 | 18 | 18 |
| `routing-decision-v1` | `14218522af2e2efb20b3abb3ea520a243cf1f75d0269e019c594587444ffeb8d` | none-mid:6, none-strong:6, none-weak:6, rubric-mid:6, rubric-strong:5, rubric-weak:6, shortcuts-mid:6, shortcuts-strong:6, shortcuts-weak:6 | 54 | 54 |
| `skill-pyeng-v1` | `3409b2cb89ba14949d45bcf2b88df3ef2e080eced4bd4db7d1c191d708916c88` | bare:4, generic-nudge:4, pyeng-skill:6 | 17 | 17 |
| `tu-grounding-e2e-v1` | `0afef71ae5de90cd8455da38d96d3775a716c53ce63b08ef91760acadf2914b5` | control-haiku:3, control-opus:3, control-sonnet:3, drift-sonnet:3, treatment-haiku:3, treatment-opus:3, treatment-sonnet:3 | 21 | 21 |
| `tu-grounding-v1` | `59ffe9c7330a44439653770c6e28155793dd0bca5712e5bc2796d72f3958c7b9` | armed-haiku:3, armed-opus:2, armed-sonnet:3, bare-haiku:3, bare-opus:3, bare-sonnet:3 | 27 | 27 |
| `verif-lift-bug-v1` | `038fa86e598cc6dcb392c0744e74c71e00a4a1c9eab8686fa0421ef350347423` | bare:10, bare-gate:10, placebo-gate:10, skill:10, skill-gate:10, skill-vnext:10 | 61 | 61 |
| `verif-lift-data-v1` | `b74dc10f647a38f7f71c06da789ab01df7f2c12d3c48cf037a8428424514dba0` | bare:10, skill:12, skill-vnext:10 | 33 | 33 |
| `verif-lift-null-v1` | `6249a43bcca6462e817d7fda1154e3fd5e53f5883b117e0a4e8260dcf78fd548` | bare:6, skill:6 | 13 | 13 |
| `verif-lift-trunc-v1` | `32ece351ccb9a50497ed59986f44a45bd01d5db83c7de1f896345e229439262a` | bare:10, skill:10 | 20 | 20 |
