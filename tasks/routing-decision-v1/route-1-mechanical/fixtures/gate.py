"""Baseline gate: the brief set is intact and matches the manifest."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    manifest = json.loads((HERE / "briefs" / "manifest.json").read_text(encoding="utf-8"))
    expected = sorted(manifest["brief_ids"])
    found = sorted(p.stem for p in (HERE / "briefs").glob("*.md"))
    if expected != found:
        print(f"brief set drifted: expected {expected}, found {found}")
        return 1
    for bid in expected:
        if not (HERE / "briefs" / f"{bid}.md").read_text(encoding="utf-8").strip():
            print(f"brief {bid} is empty")
            return 1
    print(f"ok: {len(expected)} briefs intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
