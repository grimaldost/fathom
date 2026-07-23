# Does tool granularity matter for a metadata context server? — dc-granularity-v1 findings

- **Date:** 2026-07-11. Bank: `dc-granularity-v1` (3 Q&A tasks over the data-context
  treasury corpus). Pre-v4 gate #1 for the data-context project: the result feeds the
  v4 metric-contract design before contracts freeze.
- **Question (operator):** does the data-context product surface (FINE — twelve
  discovery/actuation MCP tools) beat a COARSE merged facade (three tools: `find_data`
  / `describe_dataset` / `corpus_status`) for an agent answering analyst/manager
  questions over the real treasury corpus — on correctness and on economy?

## What was run

- **Arms as plugin-bundled MCP servers** (`scenarios/dc-granularity/assets/plugin-a`
  = fine, `plugin-b` = coarse). Both plugins are named `dc` with server key `data`,
  so the agent-visible tool prefix (`mcp__plugin_dc_data__…`) is identical across
  arms — no priming. The corpus snapshot (treasury-prod, 23 entities / 16 edges /
  20 assertions / 13 terms) is frozen INSIDE each plugin dir, entering `config_hash`
  via the plugin tree_sha. The coarse facade is built on the same backend, freshness
  engine, and provenance envelope as the product server — only granularity differs.
- **Tasks** (persona-shaped, arm-neutral instructions, `answers.json` + blind
  verifier each): `analyst-lineage` (cupom cambial upstream locators, 2-hop distinct
  count, downstream count, rate convention, alias resolution), `manager-trust`
  (freshness verdicts incl. the no-assertion honest-unknown case, snapshot
  provenance), `governance-serving` (PIT/look-ahead term, unit conventions, serving
  instructions, holiday-calendar disambiguation). 19 criteria total.
- **Oracle:** every expected value frozen from EXECUTED in-process drives of both
  arm servers; both arms returned identical facts on every probed question before
  any spend.
- **Matrix:** 2 arms × 3 tasks × 3 repeats = 18 trials, `claude-sonnet-5`, effort
  medium, single-session, headless default-deny. Smoke 8/8 the same session.

## Result — near-equivalence; the only gap is multi-hop lineage precision

| Arm | Pass | Per-criterion | Turns (total) | Tokens | Est. USD |
|---|---|---|---|---|---|
| fine-sonnet | 8/9 (88.9%, CI [56.5, 98.0]) | 17/19 at 100%; `count_2hop_correct` 2/3; `upstream_locators_exact` 2/3 | 117 | 19,564 | $2.57 |
| coarse-sonnet | 7/9 (77.8%, CI [45.3, 93.7]) | 17/19 at 100%; `count_2hop_correct` 1/3; `upstream_locators_exact` 1/3 | 95 | 20,968 | $3.05 |

- **17 of 19 criteria saturated at 100% in BOTH arms** — single-hop discovery,
  alias resolution, freshness honesty (verdict + machine reason), snapshot
  provenance, glossary navigation, unit conventions, serving instructions, and
  entity disambiguation are all granularity-insensitive at this corpus scale and
  model tier. Zero infra errors; `answers_valid` 18/18.
- **All three failed trials (2 coarse, 1 fine) failed the SAME criterion pair on
  the same task** — the 2-hop distinct-upstream count and the exact 1-hop upstream
  locator set. The failure mode is shared across arms: both surfaces return
  lineage as bare URN lists, leaving dedupe/count/locator-join to the agent.
- **Economy is a wash.** Fine spends more turns (13.0 vs 10.6 mean); coarse spends
  more tokens per response (fat digests) and slightly more USD. Both Pareto-starred.
  Full matrix: **$5.63 actual vs $36.00 advisory ceiling**, ~9 min wall.

## Interpretation

1. **Granularity is not the lever** for this workload: nothing outside lineage
   discriminated, and the economy difference is noise-level. The mega-tool-vs-many-
   tools debate, at this corpus scale on a mid-tier model, is settled by neither
   quality nor cost.
2. **The lineage payload contract is the lever.** The one discriminating region
   failed for a reason both arms share: the server hands the agent raw URN lists
   and the agent does arithmetic. Fine's directional edge (2/3 vs 1/3) is not
   protection — 1/3 of fine trials still failed.
3. **Verdict for data-context v4:** keep the twelve-tool product surface (it won
   directionally and is the natural product shape); fix `get_lineage`'s payload —
   return the distinct upstream/downstream set with an explicit count, hop labels,
   and locator-joined entries (URN + serving locator per row). That kills the
   observed error class server-side regardless of surface granularity, and it is
   a contract change, not a surface redesign.
4. **Caveats:** n=3 per cell and one model tier — directional, not final (the CIs
   overlap broadly). A larger corpus would stress the coarse arm's token growth
   (its digests scale with entity richness; the fine surface pays per question);
   re-run at scale before treating the economy tie as durable.
