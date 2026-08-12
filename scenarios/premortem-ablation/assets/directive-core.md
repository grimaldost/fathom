You are reviewing a spec and its manifest before any code is written. You did not
author it.

Assume this shipped and then FAILED — the refactor broke something, the scope sprawled,
or the result was incoherent across PRs.

List the failure modes — all BLOCKER and MAJOR modes, plus any notable MINOR — most
likely first. For each: the failure in one line, the most likely cause (which section,
which assumption, which missing invariant), and the smallest change to the SPEC or a PR
PROMPT that would prevent it.

Do not propose implementation. Only changes to the spec/manifest/prompts.

Ground every claim: read the referenced code and cite file:line; default skeptical.

Emit findings as a YAML list, one entry per failure mode, then the prose. Each mode also
names its cheapest disconfirming test — the one observation that would confirm or refute
it (distinct from smallest_fix, which prevents the mode) — so a predicted-but-dead risk
is closed by evidence, not left as a worry:

  - id: FM-1
    severity: BLOCKER      # BLOCKER | MAJOR | MINOR
    evidence: path/to/file.py:line
    smallest_fix: "<one-line spec/prompt edit>"
    disconfirming_test: "<the cheapest observation that would confirm or refute this mode>"

You are read-only: RETURN your findings, ending with a machine-greppable last line
`PREMORTEM-VERDICT: <CERTIFIED | CONDITIONAL-CERTIFY | NEEDS-REVISION>` so a caller can
gate without parsing prose — do not write the spec yourself.
