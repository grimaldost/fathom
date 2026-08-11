"""Shared verifier for the pre-mortem directive ablation bank (harness-side, blind).

Reads the candidate's work ONLY from the result-view path handed in ``argv[1]``. No
scenario identity reaches this module in argv or env (ADR-0003): every arm gets the
same task, the same fixtures and the same instruction, and only the injected system
prompt differs — which this verifier never sees.

What it scores, and what it deliberately does NOT
-------------------------------------------------
It scores the **structural contract** of a pre-mortem: the emitted findings parse,
carry a severity from the fixed vocabulary, a ``file:line`` anchor, a smallest fix and
a disconfirming test, and the pass ends in a machine-greppable verdict token.

It does NOT try to decide whether a finding is a *real* BLOCKER, and it does not match
free text against a truth list. Matching paraphrased findings against a key is a judge,
not a verifier, and a paraphrase scored as a miss would manufacture a null in the
compressed arm's favour — the direction the retirement decision already leans. That
adjudication is a separate, human, blinded pass and is not part of this bank
(``docs/specs/2026-08-11-cross-project-gate-banks.md`` Gate A).

The criteria fall into three classes, and the report must keep them apart:

``ask/shared``
    Requested by BOTH the full directive and the compressed core. A gap here is the
    extra prose buying compliance with something both arms asked for.
``behaviour``
    Requested by NEITHER in these words: whether the anchors the reviewer emitted
    actually resolve to a real file at a real line in the surface it was given. This
    is the closest deterministic proxy to groundedness the bank has, and it is the
    load-bearing criterion.
``ask/full-only``
    Requested by the full directive alone. A gap here measures what compression costs
    in FORM, which is a real finding about the directive and is not evidence about
    finding quality.

Stdlib only, no YAML dependency: the findings block is parsed line-wise, tolerantly
(a reviewer that indents differently is not scored down for it).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FINDINGS_FILE = "findings.md"
SEVERITIES = {"BLOCKER", "MAJOR", "MINOR"}
VERDICTS = ("CERTIFIED", "CONDITIONAL-CERTIFY", "NEEDS-REVISION")
MIN_FINDINGS = 3

CRITERIA = (
    "findings_written",
    "findings_ge_3",
    "severity_vocabulary",
    "every_finding_cites_evidence",
    "every_finding_smallest_fix",
    "every_finding_disconfirming_test",
    "verdict_token",
    "citations_path_exists",
    "citations_line_in_range",
    "unverified_offline_line",
    "reviewer_identity",
    "target_section_present",
)

_ID_RE = re.compile(r"^\s*-\s+id\s*:\s*(\S.*)$")
_KV_RE = re.compile(r"^\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
_VERDICT_RE = re.compile(r"^\s*PREMORTEM-VERDICT\s*:\s*(" + "|".join(VERDICTS) + r")\b(.*)$")
_UNVERIFIED_RE = re.compile(r"^\s*Unverified-offline\s*:\s*(\d+)\s*$")
# A repo-root-relative anchor: <path>:<line>, optionally wrapped in backticks/quotes.
_ANCHOR_RE = re.compile(r"^[`'\"]?([A-Za-z0-9_./\\-]+?):(\d+)[`'\"]?")


def _strip(value: str) -> str:
    return value.strip().strip('"').strip("'").strip()


def parse_findings(text: str) -> list[dict[str, str]]:
    """Every ``- id:`` block in *text*, as a list of flat key->value dicts."""
    findings: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        m = _ID_RE.match(line)
        if m:
            if current is not None:
                findings.append(current)
            current = {"id": _strip(m.group(1))}
            continue
        if current is None:
            continue
        kv = _KV_RE.match(line)
        if kv:
            key, value = kv.group(1), _strip(kv.group(2))
            # First write wins: a later prose line reusing a key name must not
            # overwrite the structured value.
            current.setdefault(key, value)
            continue
        # A non-indented, non-blank line ends the YAML block.
        if line.strip() and not line.startswith((" ", "\t", "-")):
            findings.append(current)
            current = None
    if current is not None:
        findings.append(current)
    return findings


def _anchor(value: str) -> tuple[str, int] | None:
    m = _ANCHOR_RE.match(value.strip())
    if not m:
        return None
    return m.group(1).replace("\\", "/"), int(m.group(2))


def _line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0


def _terminal_lines(text: str) -> tuple[str | None, str | None]:
    """The last non-blank line and the one before it."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None, None
    return lines[-1], (lines[-2] if len(lines) > 1 else None)


def grade(root: Path) -> dict[str, bool]:
    findings_path = root / FINDINGS_FILE
    if not findings_path.is_file():
        # Every criterion is false rather than absent: an un-written review is a
        # measured failure of the review, not a harness error.
        return dict.fromkeys(CRITERIA, False)

    text = findings_path.read_text(encoding="utf-8", errors="replace")
    findings = parse_findings(text)
    last, penultimate = _terminal_lines(text)

    verdict_m = _VERDICT_RE.match(last) if last else None

    anchors = [_anchor(f.get("evidence", "")) for f in findings]
    resolved = [(root / a[0]) if a else None for a in anchors]

    def _all(pred, seq) -> bool:
        seq = list(seq)
        return bool(seq) and all(pred(x) for x in seq)

    return {
        "findings_written": bool(text.strip()),
        "findings_ge_3": len(findings) >= MIN_FINDINGS,
        "severity_vocabulary": _all(
            lambda f: f.get("severity", "").upper() in SEVERITIES, findings
        ),
        "every_finding_cites_evidence": _all(lambda a: a is not None, anchors),
        "every_finding_smallest_fix": _all(
            lambda f: bool(f.get("smallest_fix", "").strip()), findings
        ),
        "every_finding_disconfirming_test": _all(
            lambda f: bool(f.get("disconfirming_test", "").strip()), findings
        ),
        "verdict_token": verdict_m is not None,
        "citations_path_exists": _all(lambda p: p is not None and p.is_file(), resolved),
        "citations_line_in_range": _all(
            lambda pair: (
                pair[0] is not None
                and pair[1] is not None
                and pair[0].is_file()
                and 1 <= pair[1] <= _line_count(pair[0])
            ),
            [(p, a[1] if a else None) for p, a in zip(resolved, anchors, strict=True)],
        ),
        "unverified_offline_line": bool(penultimate and _UNVERIFIED_RE.match(penultimate)),
        "reviewer_identity": bool(verdict_m and verdict_m.group(2).strip()),
        "target_section_present": _all(
            lambda f: bool(f.get("target_section", "").strip()), findings
        ),
    }


# The correctness gate: a review happened at all and ended in a greppable verdict.
# Everything else is per-criterion signal, which is where this bank discriminates.
GATE = ("findings_written", "verdict_token")


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve()
    criteria = grade(root)
    print(json.dumps(criteria, sort_keys=True))
    return 0 if all(criteria[k] for k in GATE) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
