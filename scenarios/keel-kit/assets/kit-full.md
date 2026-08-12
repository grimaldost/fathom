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
acceptance-criterion floor to the document. `Phases: Decide+Specify (Decompose: skipped)` relaxes
the manifest alone. A section that IS present is still fully checked. `Kit:` is the kit version
this spec was scaffolded from — keep it; `check-ready` (W1) warns on skew, and on its absence.*

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

## Enforcement status

| Invariant | Status | Gate/mechanism |
|---|---|---|
| <invariant key> | enforced \| review-only \| planned \| absent | <the gate, when enforced> |

*check-ready (A10): no prose may claim an invariant is "enforced" / "guaranteed" unless its
row here is `enforced`. Checked only when this table is present; a claim inside backticks, or
one negated ("not enforced", "to be enforced later"), does not fire.*

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

*Reuse notation: pin a reuse target as `**Model-on:** <backticked path>` or
`**Reuse:** <backticked path::symbol>`; `check-ready` (A9) resolves the path, and the symbol
when given — so a spec cannot say "model-on / reuse X" without X actually existing.*

*Anchor ranges: a multi-line citation is `` `path:lo-hi` ``; `check-ready` (A11) resolves the file
and the `hi` line, and for a `.py`/`.pyi` anchor additionally flags a range that opens a
bracket/brace/paren it does not close, so a citation cannot silently truncate a collection literal
mid-structure. Quote a literal complete or not at all.*

*Gate-adversarial examples: when the spec must QUOTE something the gate itself scans for — a
literal `Verdict:` line, a bare to-do placeholder token, an example `### heading` — put it inside a
code fence; fenced content is masked before every check, while the same example unfenced can
false-fail (A3) or shadow the real certification (B1).*

*Out-of-wave consumers: when a section MOVES, RENAMES, or RETYPES a symbol, or strips content from a
file, list every consumer beyond the import graph — scripts that regex/parse the file's TEXT
(docs-sync checks, doc anchors, tests reading it as data) and every READER of a retyped symbol — and
add each to that PR's file-list. (Not gated; the pre-mortem attacks it.)*

*Measurement / experiment specs: fill the optional `## Experiment design (Part B)` section below — the
eval/experiment DoR items (`definition-of-ready.md`, Part B) gate the axes it names.*

*Counting: a test-count tripwire counts pytest ITEMS (post-parametrize collection), not function
defs, and shows the parametrize expansion; enumerate code constructs by AST, never a bare text grep
(grep is a superset pre-filter only); pin both the UNIT and the AUTHORITY of any recount.*

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

*Release-notes-in-wave: any section that adds public surface or changes behaviour carries its
CHANGELOG entry (and a migration-guide section, if consumer-facing) in the SAME wave — release-notes
completeness is a per-wave exit condition, not a terminal-audit cleanup; a consistency gate (e.g. a
docs-sync check) verifies cross-references, not completeness.*

## Experiment design (Part B)

*(Measurement / experiment specs only — delete this whole section for a code spec. The eval/experiment DoR
items (`definition-of-ready.md`, Part B) gate these axes; the reviewer certifies the design, `keel
check-ready` the certification. Fill the `<...>` placeholders; this is a `##` section, so it needs no
acceptance criterion and carries no anchors.)*

- **Estimand + unit of analysis:** <the effect measured, at what grain — per-item delta vs aggregate>
- **Reps / power & MEWD:** <N per arm; the minimum effect worth detecting; why N can detect it — a 1-rep delta is noise>
- **Blinding + held-constant factors:** <what is blinded; what is held equal across arms>
- **Correctness oracle (not "ran green"):** <what decides "correct", distinct from the run completing>
- **Measured-unit causal path:** <treatment end — the measured path READS what the treatment changes (not inert); measured-unit end — capabilities beyond the intended input enumerated, no side channel to the ground truth>
- **Enforcement of isolation invariants:** <each leakage/isolation invariant, and the buildable mechanism that enforces it, claimed by a numbered section/PR>
- **Pre-registered analysis plan:** <the analysis fixed before results are seen>

## Pre-mortem certification

*The externalized correctness pass (`pre-mortem-prompt.md`), certified by a fresh
reviewer who did NOT author this spec. `keel check-ready` does not pass until the
verdict is `CERTIFIED` (ADR-0002). A freshly-scaffolded spec is, correctly, not Ready.
Save the pass's returned output to the sibling `<spec-stem>.premortem.md` (header: spec path,
date, reviewer, `Spec-hash:` from `keel spec-hash`) and name it below — `check-ready` B2 verifies
a named artifact's existence, verdict agreement, and spec-hash currency. B2 raises the cost of
forging a certification; it does not prove the pass was blind — that residual trust stays named.*

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
reviewable. `check-ready` (A12) holds each `artifact:line` to a resolving anchor — it verifies the
fold was recorded against a real line, not that it is correct (that is the reviewer's job). A row's
anchor MAY carry a backticked snippet (`` `path:line` `snippet` ``): A12 then verifies the snippet
matches that line, so an in-range edit that moves the anchored content no longer decays silently. Leave the
header only (no data rows) and A12 dozes. The ledger must be the FIRST table under this `### Fold ledger`
heading — A12 reads only the first contiguous table, so a round-history / disposition table belongs in
its own section, not after the ledger here.*

| Finding | Target section | artifact:line | Confirmed |
|---|---|---|---|

---
*This template is structured so that most of the deterministic Definition-of-Ready
checks (`definition-of-ready.md`) pass by construction: numbered sections,
per-section acceptance criteria, the concept→module map, and the PR↔section
manifest are all required fields. The one field NOT satisfied by construction is the
pre-mortem certification — a non-author reviewer must sign it, which is the point
(ADR-0002).*

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

- [ ] Every section is numbered (§1, §2, …).
- [ ] Every numbered section has a **non-trivial** acceptance criterion.
- [ ] No `TBD` / `TODO` / `FIXME` / `???` anywhere in the spec.
- [ ] PR ↔ section manifest exists; every section is covered by **exactly one** PR
      and every PR cites **exactly one** section (a bijection) — unless the header declares
      Decompose skipped, in which case an absent manifest is accepted and a present one is
      still fully checked.
- [ ] Every path in the concept→module map exists, or is explicitly marked "to be
      created" **and** claimed by a numbered section.
- [ ] The three structural sections above (numbered sections, the manifest, the concept→module
      map) are required — unless the header declares `Kind: single-change`, which relaxes all
      three to absent-ok and moves the acceptance-criterion floor to the document. A declared
      kind sizes the gate to the round; it does not weaken a section that is present.
- [ ] Every `path:line` anchor resolves (file + line exist) and any quoted snippet — the
      backticked token right after the anchor — matches.
- [ ] Every cited `docs/adr/NNNN-…` uses a number free on the base (no collision).
- [ ] Every `**Model-on:**` / `**Reuse:**` reference present resolves — the path exists
      (and the symbol, for `path::symbol`) (A9).
- [ ] Every in-text `§N` reference resolves to a numbered section (A8); the `§` glyph
      denotes this spec's own sections — a cross-document reference names the document.
- [ ] When an `Enforcement status` table is present, no prose claims an invariant
      "enforced" / "guaranteed" that the table marks review-only / planned / absent (A10).
- [ ] Every `path:lo-hi` range anchor resolves (file + `hi` line exist); for a `.py`/`.pyi`
      anchor it must additionally close (string/comment-aware) every bracket it opens (A11) —
      a citation cannot truncate a collection literal mid-structure.
- [ ] A certification that claims a non-trivial fold carries a `### Fold ledger` with a resolving
      `artifact:line` row per finding (R1); when rows are present each anchor resolves (A12); a clean
      certify (folded in: none) dozes.

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
- [ ] Every invariant the work touches is named in "Invariants touched", each with an ADR.
- [ ] Every concept maps to a module in the concept→module map.
- [ ] Every non-obvious design choice has an ADR (alternatives recorded).
- [ ] The spec is internally consistent (no section contradicts another).
- [ ] A post-fold coherence re-read was performed and recorded (`Post-fold coherence:` in
      the certification): each folded finding is applied consistently across all sections,
      and any scope-narrowing finding had its dependent counts re-derived.
- [ ] *(eval/experiment specs)* each measured criterion carries a one-line baseline expectation —
      will the control / `bare` arm plausibly pass it? — and the reviewer flagged ceiling/floor risk:
      a procedurally-perfect spec still measures nothing if its criteria cannot vary across arms.
- [ ] *(eval/experiment specs)* instrument defeatability — the reviewer asked the cheapest way an
      agent sidesteps the planted difficulty (a tool, a shortcut, a grep) so the run measures nothing;
      an instrument trivially bypassed yields a null for a reason the design never controlled (distinct
      from the ceiling/floor question above).
- [ ] *(eval/experiment specs)* feasibility-grounding ran FIRST — before internal-validity attacks, the
      reviewer grounded the headline's key variable against the empirical record it needs (prior-run
      data/ledger, the reused instrument); if that record cannot supply the variation the study measures,
      the study is null on these instruments and the rest of the review short-circuits.
- [ ] *(eval/experiment specs)* the experimental design is named, not just the subject: the estimand +
      unit of analysis (per-item delta vs aggregate); enough reps to detect the minimum effect worth
      detecting — a 1-rep delta is noise (a power question, distinct from feasibility above: power is
      whether N can detect the effect, feasibility is whether the record supplies the variable); blinding
      + held-constant factors; and a correctness oracle distinct from "ran green" (distinct from the
      baseline-expectation item).
- [ ] *(eval/experiment specs)* the causal path the study assumes is traced against code from BOTH ends:
      the measured path actually READS what the treatment changes (a treatment the measured call recomputes
      live or never reads is inert — mis-built, not null; distinct from feasibility), and the measured
      unit's capabilities beyond the intended input (tools, network, filesystem + cwd, prior/session state)
      include no side channel to the ground truth (a side channel CONFOUNDS the result — distinct from
      defeatability's null).
- [ ] *(eval/experiment specs)* every isolation / safety / leakage invariant the spec asserts names a
      buildable enforcement mechanism claimed by a numbered §/PR — not a bare assertion, and not a smoke
      that tests a jail no PR creates.
- [ ] *(eval/experiment specs)* the analysis plan is pre-registered — fixed before results are seen, not
      chosen after (the spec-template advertises this axis as DoR-gated; this is that gate).

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
  is masked from the hash by design. But if discharging a condition edits the **spec body**, the
  saved hash no longer matches, and B2's "certified against an earlier revision" WARN is then the
  *expected honest state* of this close, not a defect to silence (ADR-0002) — never recompute the
  hash after discharge to quiet it, which would record a revision the reviewer never read. The B1
  operator-accepted WARN stands the same way.
- **A confirm re-gate is optional**, priced by the round economy (ADR-0014): take one only when a
  condition outgrew its named ≤2-line bound, or the fix touches an irreversible / shared-contract
  surface. A confirm round bought only to flip the token to `CERTIFIED` is over-process — the close
  already records who accepted what, and the gate passes with its WARNs standing. When a confirm
  re-gate IS taken and returns `CERTIFIED`, its saved output becomes the certification artifact
  (latest-wins) and the recorded verdict flips with it — the ordinary close, not this one.

**Gate result:** Ready ✅ only when Part A is well-formed **and** the Part B
pre-mortem certification is recorded. `keel check-ready` enforces both halves; the
remaining Part B items are the reviewer's evidence-backed certification, not a
self-signed checkbox. The gate verifies the certification was *recorded* by a named
non-author reviewer — not that the reviewer was truly blind or right; that residual
trust is named, not hidden (ADR-0002).
