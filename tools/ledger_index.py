#!/usr/bin/env python
"""Render the ledger index — the committed, always-fresh stamp every report is read against.

The coverage ratchet (``tests/test_ledger_coverage.py``) proves a committed ledger
has *a* published verdict somewhere. It could not prove the verdict was read against
the ledger as it stands now, and that gap shipped a defect: a re-validation report
was published against a 10-trial snapshot, an eleventh trial was appended to the same
ledger in the same wave, and three documents then carried three different control-pool
sizes with three different p-values, none of them the committed state.

This tool renders one row per committed ledger: the file's sha256, the per-scenario
count of ``status == "completed"`` trials, and the raw row counts. The rendered file is
committed, and the test regenerates it and compares byte-for-byte. So any append to any
ledger turns the suite red until the index is re-rendered, and the re-render diff names
exactly which arms moved — which is the moment to re-read the documents that quote them.

What this does NOT do, stated plainly: it does not parse prose. A report that quotes a
wrong number is still a wrong number; what the index buys is that the right number is
committed, dated by hash, and adjacent, so the contradiction is mechanical to find
instead of requiring someone to re-derive it from the JSONL.

Stdlib-only. ``python tools/ledger_index.py`` checks (exit 1 when stale);
``--write`` re-renders. Both run without uv.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
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


def _rows(path: Path) -> list[dict]:
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

    `.gitattributes` pins `*.jsonl text eol=lf`, so the committed bytes are always LF.
    The working tree need not be: `ledger.py` appends through Python text mode, which
    writes CRLF on Windows, and git normalises it away again on check-in. Hashing the
    raw file therefore stamped the checkout's platform rather than the ledger, and the
    freshness gate failed on Windows against an index stamped on LF — with a message
    accusing an operator of appending to a ledger that had not moved. Normalising here
    makes the digest equal to the one over the committed blob, on every platform.
    """
    return path.read_bytes().replace(b"\r\n", b"\n")


def summarise(path: Path) -> dict:
    rows = _rows(path)
    trials = [r for r in rows if r.get("kind") == "trial"]
    runs = [r for r in rows if r.get("kind") == "run"]
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="rewrite the committed index")
    parser.add_argument("--ledger-dir", default=str(LEDGER_DIR))
    args = parser.parse_args(argv)

    text = render(Path(args.ledger_dir))
    if args.write:
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        INDEX_PATH.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {INDEX_PATH}")
        return 0
    current = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.is_file() else ""
    if current == text:
        print("ledger index is current")
        return 0
    print("ledger index is STALE — re-render with `python tools/ledger_index.py --write`")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
