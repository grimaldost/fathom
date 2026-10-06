# Method kit

How changes to the fathom engine are specified, reviewed and closed. The method is keel's
governed-series method: a spec passes a Definition of Ready before it is split into PRs, each
PR passes a Definition of Done before it merges, and what a series teaches is triaged into
durable checks. The files here are this repository's copy of keel's portable kit, bound to
fathom's own gates in [`method-bindings.md`](method-bindings.md).

A one-file fix does not need any of this; the method pays for itself when a change spans
several PRs or touches an invariant.

## Slots and the files that fill them

| Slot | File | Notes |
|---|---|---|
| Decision log | [`../adr/adr-template.md`](../adr/adr-template.md) | one numbered file per decision |
| Spec format | [`../specs/spec-template.md`](../specs/spec-template.md) | numbered sections; ready for the DoR checks by construction |
| Entry gate of decomposition | [`definition-of-ready.md`](definition-of-ready.md) | a script checks form; a non-author reviewer certifies correctness |
| Pre-mortem | [`pre-mortem-prompt.md`](pre-mortem-prompt.md) | the fresh-eyes pass that closes the DoR gate |
| Exit gate of review | [`definition-of-done.md`](definition-of-done.md) | gate commands and the blocking checklist |
| Review checklist | [`review-checklist.md`](review-checklist.md) | generic items plus fathom's own; the promotion target for triage |
| Reflection sink | [`reflection-triage.md`](reflection-triage.md) | turns what a series surfaced into checks |
| Series budget | [`series-toml-skeleton.md`](series-toml-skeleton.md) | per-phase per-spawn USD caps in `[governance.budgets]` |
| Cost terms in a comparison | [`measured-terms.md`](measured-terms.md) | a cost term a verdict rests on is measured, not modelled |
| Bindings | [`method-bindings.md`](method-bindings.md) | each slot bound to a concrete mechanism in this repository |

## Using the kit

1. Write the spec from `spec-template.md`, with every invariant it touches named and each
   backed by an ADR.
2. Run the Definition of Ready: `keel check-ready <spec>` for the form, then a non-author
   pre-mortem for the approach.
3. Split the spec into PRs, one numbered section each, and run them as a series (convoy) or
   one at a time.
4. Merge each PR only when the Definition of Done holds.
5. Triage what the series surfaced; promote each recurring trap to a checklist item, a gate or
   a template change.

`series.toml`, the orchestration hooks and the engine's own formats are convoy's; these files
link to them rather than restating them.
