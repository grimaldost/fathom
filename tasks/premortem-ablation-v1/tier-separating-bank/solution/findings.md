# Pre-mortem — tier-separating-bank

- id: FM-1
  severity: BLOCKER
  evidence: spec.md:77
  smallest_fix: "state the measured estimand and its unit of analysis in this section"
  disconfirming_test: "re-read the section and find the estimand already named"
  target_section: "section 1"
- id: FM-2
  severity: MAJOR
  evidence: spec.md:154
  smallest_fix: "name the baseline expectation for each measured criterion"
  disconfirming_test: "check whether a prior run's ledger already holds the variation"
  target_section: "section 2"
- id: FM-3
  severity: MINOR
  evidence: spec.md:231
  smallest_fix: "name the enforcement mechanism a numbered PR builds"
  disconfirming_test: "grep the PR list for the named mechanism"
  target_section: "section 3"

The three modes above are the reference shape this bank's verifier accepts; they are
here to prove the criteria are satisfiable, not to stand as a real review.

Unverified-offline: 0
PREMORTEM-VERDICT: NEEDS-REVISION reference-solution@premortem-ablation-v1
