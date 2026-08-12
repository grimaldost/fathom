The project you are working in uses a spec-first method. Its kit is reproduced below: read it and
follow it when you write or repair a design spec.

---

# Spec — <feature/refactor name>

- **Date:** YYYY-MM-DD
- **Status:** draft | ready (DoR passed) | in progress | done
- **Kit:** 0.14.0
- **Kind:** series
- **Audience:** <who/what reads this>
- **Output artifact(s):** <paths>

*`Kind:` is resolved, not a menu — leave `series` unless this spec really is one change with
nothing to decompose, then write `single-change`, which relaxes the three structural sections
(numbered sections, the PR↔section manifest, the concept→module map) to absent-ok and moves the
acceptance-criterion floor to the document.*

## Context

Why this work, and what it builds on (link the relevant ADRs).

## Goal

One or two sentences: what this delivers.

## Gate commands

The exact commands that gate this work, named precisely (scope and excludes included) so
prompts and reviewers don't guess: e.g. `ruff check .`, `uv run pytest`, and the project's
type-check invocation. State *which* command, not "the linter".

## Non-goals

What this explicitly does NOT cover. Bounds scope so workers can't sprawl.

## Invariants touched

List every architectural invariant this work could affect (boundaries, locks,
immutability, schema contracts...). Each must already have an ADR; if not, write
the ADR first. *Naming these is a DoR requirement.*

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| <concept> | `path/to/module` |

*Every concept must map to a home. A concept with no module is a DoR failure. Mark a new path
"(to be created)" and name it — full path, or bare basename when unique — in the body of the
§ that creates it (`check-ready` A5); in a greenfield spec that is every row.*

## Numbered sections

Each numbered section is a unit of work a single PR can cite. Keep them small and
single-concern.

### §1 <title>
What changes. **Acceptance criterion:** <the observable condition that means §1 is
done>.

### §2 <title>
What changes. **Acceptance criterion:** <...>.

*(Add sections as needed. Every section needs an acceptance criterion — this is
both a DoR check and each PR's exit gate.)*

*Ground factual claims with `path:line` anchors, repo-root-relative (`src/pkg/mod.py:NN`). A
backticked token on the same line right after an anchor IS its snippet: `check-ready` (A6)
requires it be an exact substring of that line — don't backtick prose emphasis or `...` elision
there. A bare anchor verifies only that the file and line exist; a claim-supporting anchor SHOULD
carry its snippet, so the gate verifies the evidence, not just the address. Cite a new ADR as
`docs/adr/NNNN-slug.md` using the next free number on your base, never a hardcoded guess.*

*Gate-adversarial examples: when the spec must QUOTE something the gate itself scans for — a
literal `Verdict:` line, a bare to-do placeholder token, an example `### heading` — put it inside a
code fence; fenced content is masked before every check, while the same example unfenced can
false-fail (A3) or shadow the real certification (B1).*

## PR ↔ section manifest

| PR | Implements section | One concern? |
|---|---|---|
| PR01 | §1 | yes |
| PR02 | §2 | yes |

*Every section must be covered by exactly one PR, and every PR must cite exactly
one section. A many-to-one or uncovered section is a DoR failure.*

## Definition of Done (this spec)

Concrete, checkable conditions for the whole spec (beyond per-section criteria).

- Generated / mirrored / snapshot artifacts downstream of touched surfaces
  (consumer-reference mirrors, golden fixtures, lockfiles), each with its freshness gate —
  or the word "none": <enumerate them here; the pre-mortem challenges this declaration>

## Pre-mortem certification

*The externalized correctness pass (`pre-mortem-prompt.md`), certified by a fresh
reviewer who did NOT author this spec. `keel check-ready` does not pass until the
verdict is `CERTIFIED` (ADR-0002). A freshly-scaffolded spec is, correctly, not Ready.*

- **Reviewer:**
- **Verdict:** not yet certified
- **Operator:** <required only when the Verdict is CONDITIONAL-CERTIFY — the named owner who accepts "ready modulo a named fix"; check-ready then passes with a WARN (B1). If the Operator applies the conditions, the verdict stays CONDITIONAL-CERTIFY with a discharge note — the operator close, definition-of-ready.md Part B>
- **Certification artifact:** <the saved pass output's path. `check-ready` reads the LEADING path token and ignores what follows, so a prior round belongs right here: `<stem>.premortem.md` (r1 at `<stem>.premortem-r1.md`)>
- **Date:**
- **Reviewed against:** <external dependency SHAs/versions reasoned against, if any>
- **Post-fold coherence:**
- **Failure modes considered & folded in:**

### Fold ledger

*Required when the certification claims a non-trivial fold (R1); a clean certify dozes: one row per folded finding so the post-fold delta is
reviewable. `check-ready` (A12) holds each `artifact:line` to a resolving anchor. Leave the
header only (no data rows) and A12 dozes. The ledger must be the FIRST table under this `### Fold ledger`
heading — A12 reads only the first contiguous table, so a round-history / disposition table belongs in
its own section, not after the ledger here.*

| Finding | Target section | artifact:line | Confirmed |
|---|---|---|---|

---

# Definition of Ready (DoR gate)

The exit gate of **Specify** / entry gate of **Decompose**. A series may not be
decomposed or run until DoR passes. Rationale: once workers are stateless and gates
deterministic, spec quality is the single point of failure (method sharpening 1) —
so spec quality gets its own gate.

DoR is **not** symmetric to the Definition of Done in mechanism, and we no longer
claim it is. DoD checks behaviour against an executable oracle (tests, types); DoR
has no oracle for "is this approach right?". So DoR splits in two: a deterministic
**Part A** (well-formedness — a script asserts it) and an externalized **Part B**
(correctness — certified by a fresh reviewer, a judgment moved to a different
context, not a machine verdict). `keel check-ready` enforces both halves: it passes
only when the spec is well-formed AND a blind pre-mortem certification is recorded
(ADR-0002). It never green-lights a spec on structure alone.

## Part A — well-formedness checks (a script asserts these)

These assert *form*, not *correctness* — a well-formed spec can still be wrong (that
is Part B's job).

### Reference: what `check_spec_ready` asserts

```
A0 the header's `Kind:` declaration, when present, must read `series` or `single-change` — an
   unknown kind is a violation naming the offending token, and relaxes nothing. `single-change`
   relaxes A1/A4/A5 to absent-ok (a present section is still checked in full) and moves A2 to
   document scope
A1 fail unless >=1 "### §N" heading under "Numbered sections", all numbered — absent-ok under a
   declared `Kind: single-change`
A2 fail unless each §N has a non-trivial "Acceptance criterion" (present, >=5 words); under a
   declared `Kind: single-change` with no numbered sections, the same floor is read over the
   whole document instead
A3 fail on a TBD/TODO/FIXME/??? token, or a leftover `<...>` angle placeholder — the angle idiom is matched on the prose view (inline-code spans space-filled, wrapped spans included), so backticked `<target>` syntax is exempt while a bare `<title>` is caught
A4 parse the PR<->section manifest: fail unless bijection(PRs, sections), full coverage — relaxed to absent-ok when the header declares `- **Phases:** ... (Decompose: skipped)` or `- **Kind:** single-change`; a manifest that IS present is still checked in full (ADR-0014)
A5 each concept->module path: fail unless exists(path) or ("to be created" and claimed by a §) — absent-ok under a declared `Kind: single-change`
A6 each `path:line` anchor: fail unless file exists, line in range, and any quoted snippet (the backticked token right after the anchor) matches
A7 each cited `docs/adr/NNNN-...md`: fail unless that number is free on the base or names that ADR
A8 each bare intra-spec `§N` reference: fail unless it names a numbered section — detection on the prose view (a backticked `§N` mention is exempt); skips `§N.M`, headings, and doc-cued refs including a joined range (`ADR-0103 §3/§4`, an en-dash range)
A9 each `**Model-on:**`/`**Reuse:**` reference present: fail unless the path exists (and the symbol, for `path::symbol`)
A10 when an Enforcement-status table is present: fail if prose claims an invariant "enforced"/"guaranteed" whose row is not enforced
A11 each `path:lo-hi` range anchor: the file and `hi` line must resolve; for a `.py`/`.pyi` anchor it must additionally close (string/comment-aware) every bracket it opens (single-line `path:line` anchors stay A6)
A12 when a `### Fold ledger` sub-table is present: fail unless each row carries an `artifact:line` confirmation that resolves — read from whichever cell IS one, so an extra column (round, severity, disposition) does not break it; a row wider than its own header is a column break and fails as one
R1 a certification claiming a non-trivial fold must carry a `### Fold ledger` with >=1 resolving row (a deliberate tightening, not verify-when-present; a clean certify dozes)
B1 fail unless a "## Pre-mortem certification" block records Verdict: CERTIFIED (or CONDITIONAL-CERTIFY + a named Operator) + a Reviewer
B2 when the certification names a `Certification artifact:`: the field's LEADING path token is the artifact (trailing prose — a round note, a prior-round path — is ignored); fail unless the file exists and its last line-anchored PREMORTEM-VERDICT token agrees with the recorded Verdict; WARN (not fail) on a Spec-hash mismatch ("certified against an earlier revision" — suffixed with the operator-close pointer when the recorded verdict is an operator-accepted CONDITIONAL-CERTIFY) and when no artifact is named (adoption nudge)
W1 (warn) the header's `- **Kit:** X.Y.Z` stamp (or a legacy `<!-- keel kit X.Y.Z -->` comment) from a different kit MAJOR.MINOR than the running gate warns of kit<->gate skew; a patch difference is silent, and an UNSTAMPED spec warns too — a spec that declares no kit version is one on which skew is undetectable
W2 (warn) a header `Status:` still reading `draft` while a CERTIFIED / CONDITIONAL-CERTIFY certification is recorded warns that the coordinate system is stale; silent when there is no Status field, when Status has moved past draft, or when nothing is certified
W3 (warn) an anchor that does not resolve as written but whose basename matches exactly ONE repo file (vendor trees excluded) resolves to that file and warns, naming the expansion — the shorthand a fresh reviewer emits stops manufacturing gate failures; ambiguity or no match still fails (A6/A11/A12)
```
*(A2/A5 detect absence/triviality, not semantic wrongness — Part A cannot judge
"right." That is Part B.)*

## Part B — correctness, certified (a fresh, non-author reviewer certifies, with evidence)

Not mechanizable as form. Externalized: a reviewer who did **not** author the spec
runs the pre-mortem (`pre-mortem-prompt.md`) and records a verdict in the spec's
`## Pre-mortem certification` block. This is **required**, not recommended — it is the
only check aimed at "this approach is wrong," the dominant defect class once workers
are stateless.

- [ ] A pre-mortem pass has been run by a non-author reviewer, and the certification
      block records `Verdict: CERTIFIED` — or `CONDITIONAL-CERTIFY` with a named `Operator:`
      (operator-accepted, ready modulo a named fix; `check-ready` passes with a WARN, not EXIT 1).
      *(`keel check-ready` enforces this — B1.)*
- [ ] The pass's returned output is saved (`<spec-stem>.premortem.md`, with a `Spec-hash:` from
      `keel spec-hash`) and named in the certification's `Certification artifact:` field.
      *(`keel check-ready` verifies a named artifact — B2, verify-when-present: existence, verdict
      agreement, hash currency; forgery cost, not blindness proof.)*

### The operator close (discharging a CONDITIONAL-CERTIFY)

When the final pass returns `CONDITIONAL-CERTIFY` and the named Operator applies the bounded
`conditions:` themselves, the sanctioned close is:

- **The recorded `Verdict:` stays `CONDITIONAL-CERTIFY`**, with the named `Operator:` and a discharge
  note on the verdict line (e.g. `CONDITIONAL-CERTIFY — COND-1 discharged by the Operator, <date>`);
  record each discharged condition as a fold-ledger row so A12 anchors the fix to a real line. Do not
  rewrite the verdict to `CERTIFIED`: no pass returned that token, and B2 fails a recorded Verdict
  that disagrees with the saved artifact's.
- **The artifact's `Spec-hash:` stays the hash of the spec the final pass read.** The close's own
  recording never moves the hash — a certification-block edit (the discharge note, a fold-ledger row)
  is masked from the hash by design.
- **A confirm re-gate is optional**, priced by the round economy (ADR-0014): take one only when a
  condition outgrew its named ≤2-line bound, or the fix touches an irreversible / shared-contract
  surface.

**Gate result:** Ready ✅ only when Part A is well-formed **and** the Part B
pre-mortem certification is recorded. `keel check-ready` enforces both halves; the
remaining Part B items are the reviewer's evidence-backed certification, not a
self-signed checkbox. The gate verifies the certification was *recorded* by a named
non-author reviewer — not that the reviewer was truly blind or right; that residual
trust is named, not hidden (ADR-0002).
