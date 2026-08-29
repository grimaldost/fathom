"""Rendering the ledger index — the committed stamp every verdict is read against.

The logic lives here, under ``src/fathom/``, because :mod:`fathom.reconcile` needs it and
``src/`` may never import ``tools/``.  ``tools/ledger_index.py`` stays the operator-facing
CLI and re-exports these names, so ``python tools/ledger_index.py --write`` and the
existing ``import ledger_index`` in the tests keep working unchanged.

The coverage ratchet (``tests/test_ledger_coverage.py``) proves a committed ledger has *a*
published verdict somewhere.  It could not prove the verdict was read against the ledger as
it stands now, and that gap shipped a defect: a re-validation report was published against a
10-trial snapshot, an eleventh trial was appended to the same ledger in the same wave, and
three documents then carried three different control-pool sizes with three different
p-values, none of them the committed state.

This module renders one row per committed ledger: the file's sha256 over canonical bytes,
the per-scenario count of ``status == "completed"`` trials, and the raw row counts.  The
rendered file is committed and the reconciliation regenerates it and compares byte-for-byte,
so any append to any ledger turns the suite red until it is re-rendered — and the re-render
diff names exactly which arms moved, which is the moment to re-read the documents quoting
them.

What this does NOT do, stated plainly: it does not parse prose.  A report that quotes a
wrong number is still a wrong number; what the index buys is that the right number is
committed, dated by hash, and adjacent, so the contradiction is mechanical to find instead
of requiring someone to re-derive it from the JSONL.

Stdlib only.
"""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER_DIR = REPO / "ledger"
INDEX_PATH = REPO / "docs" / "reports" / "LEDGER-INDEX.md"

HEADER = """# Ledger index — the stamp every verdict is read against

**Generated. Do not hand-edit.** Re-render with `python tools/ledger_index.py --write`;
`tests/test_ledger_coverage.py` fails while this file and `ledger/` disagree.

One row per committed ledger (archived ledgers under `ledger/archive/` are excluded, per
the coverage ratchet). `n by arm` counts trial rows with `status == "completed"` only —
the same rule the resume key and every scorecard use, so an errored trial is never a
measured failure. A document that quotes a per-arm n, a pooled control total or a p-value
for one of these banks is quoting *this* row; if it disagrees, the document is stale.

| Bank | ledger sha256 | n by arm (completed) | trial rows | run rows |
|---|---|---|---|---|
"""


def ledger_files(ledger_dir: Path) -> list[Path]:
    """Committed ledgers, top level only — ``ledger/archive/`` is deliberately excluded."""
    if not ledger_dir.is_dir():
        return []
    return sorted(ledger_dir.glob("*.jsonl"))


def rows(path: Path) -> list[dict]:
    """Every JSON object in a ledger, skipping blank and malformed lines."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def canonical_bytes(path: Path) -> bytes:
    """The ledger as git stores it: LF line endings, whatever the checkout has.

    ``.gitattributes`` pins ``*.jsonl text eol=lf``, so the committed bytes are always LF.
    The working tree need not be: ``ledger.py`` appends through Python text mode, which
    writes CRLF on Windows, and git normalises it away again on check-in.  Hashing the raw
    file therefore stamped the checkout's platform rather than the ledger, and the freshness
    gate failed on Windows against an index stamped on LF — with a message accusing an
    operator of appending to a ledger that had not moved.  Normalising here makes the digest
    equal to the one over the committed blob, on every platform.
    """
    return path.read_bytes().replace(b"\r\n", b"\n")


def summarise(path: Path) -> dict:
    """One index row's facts for a single ledger."""
    parsed = rows(path)
    trials = [r for r in parsed if r.get("kind") == "trial"]
    runs = [r for r in parsed if r.get("kind") == "run"]
    completed: collections.Counter[str] = collections.Counter(
        str(r.get("scenario") or "(unnamed)") for r in trials if r.get("status") == "completed"
    )
    return {
        "bank": path.stem,
        "sha256": hashlib.sha256(canonical_bytes(path)).hexdigest(),
        "completed": dict(sorted(completed.items())),
        "trial_rows": len(trials),
        "run_rows": len(runs),
    }


def render(ledger_dir: Path = LEDGER_DIR) -> str:
    """The whole index document, as it should be committed."""
    lines = [HEADER.rstrip("\n")]
    for path in ledger_files(ledger_dir):
        s = summarise(path)
        by_arm = (
            ", ".join(f"{arm}:{n}" for arm, n in s["completed"].items()) or "— (none completed)"
        )
        lines.append(
            f"| `{s['bank']}` | `{s['sha256']}` | {by_arm} | {s['trial_rows']} | {s['run_rows']} |"
        )
    lines.append("")
    return "\n".join(lines)
