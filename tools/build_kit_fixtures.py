"""Generate keel-kit-ablation-v1's task dirs from the one shared staged tree.

Eight tasks stage the SAME invented package (`_tree/`, the `tinyetl` batch loader) and differ only
in the brief or the defective spec laid over it. Copying that tree by hand eight times is how a
fixture silently diverges between tasks, and `profile.json`'s `staged_sha256` — the integrity
criterion that notices an arm editing the staged code — would then protect the wrong bytes. So the
tree is the source and this script is the only thing that writes fixtures, task.toml, verify.py
and profile.json.

Idempotent. Hand-authored material (`solution/`, `refs/skeleton/`, and each repair task's
defective `fixtures/spec.md`) is never touched; a brief is rewritten only under --force-briefs.

    python tools/build_kit_fixtures.py [--force-briefs]

Any fixture change means bumping the bank's `dataset_version` — it is in the resume key.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

BANK = Path(__file__).resolve().parent.parent / "tasks" / "keel-kit-ablation-v1"
TREE = BANK / "_tree"

SHARED = [
    "gate_part_a_passes",
    "numbered_sections_present",
    "manifest_is_bijection",
    "every_section_has_criterion",
    "no_placeholders",
]
BEHAVIOUR = [
    "anchors_resolve",
    "concept_map_paths_resolve",
    "section_refs_resolve",
    "criteria_name_runnable_command",
    "brief_requirements_covered",
]
NOTE_ONLY = ["enforcement_claims_clean", "reuse_refs_resolve", "range_anchors_balanced"]
INTEGRITY = [
    "no_self_certification",
    "anchors_point_at_staged_files",
    "staged_tree_untouched",
]

AUTHORING_INSTRUCTION = """\
This repository is `tinyetl`, a small batch loader for order records. `brief.md` at the root of
the workspace describes a change that has been asked for; it has not been designed or implemented
yet.

Write the design spec for that change to a file named `spec.md` at the root of this workspace.
Whatever the spec asserts about the code must be true of the files staged here.

Do not implement the change, and do not modify any staged file — `spec.md` is the only file you
create or edit.
"""

REPAIR_INSTRUCTION = """\
This repository is `tinyetl`, a small batch loader for order records. `spec.md` at the root of the
workspace is the design spec for a change to it, and it is inconsistent: {defect}

Repair `spec.md` so the document is internally consistent and everything it asserts about the
staged code is accurate.

Do not implement the change, and do not modify any staged file — `spec.md` is the only file you
edit.
"""

TASKS: dict[str, dict] = {
    "author-cli-flag": {
        "shape": "authoring",
        "tokens": ["--region", "KNOWN_REGIONS", "UnknownRegionError"],
        "brief": """\
# Brief — filter a batch by region

Operators running `tinyetl` against the shared order feed want to process one region at a time
instead of the whole feed.

What is wanted:

1. A `--region` option on the command line. Given `--region north`, the run processes only the
   rows whose `region` column is `north`; without it the run behaves exactly as it does today.
2. The option accepts only a region already listed in `KNOWN_REGIONS`. Anything else stops the
   run with a new `UnknownRegionError` rather than silently producing an empty batch.
3. The run summary keeps reporting the number of rows actually written.

Nothing about the record shape on disk changes.
""",
    },
    "author-schema-evolve": {
        "shape": "authoring",
        "tokens": ["retry_after_s", "schema_version", "migrate_v1_to_v2"],
        "brief": """\
# Brief — carry a retry hint on every record

The two jobs that read the record stream have to re-poll a source when a batch lands late, and
today they guess how long to wait.

What is wanted:

1. Every written record carries a new `retry_after_s` field: an integer number of seconds a reader
   should wait before re-reading. It is derived from the batch, not supplied per row.
2. `schema_version` moves from 1 to 2, because a reader must be able to tell the two shapes apart.
3. A `migrate_v1_to_v2` conversion exists so an already-written v1 file can be read as v2 without
   re-running the batch that produced it.

Records already on disk must stay readable.
""",
    },
    "author-two-consumer": {
        "shape": "authoring",
        "tokens": ["reporting-daily", "alerting-hourly", "row_count"],
        "brief": """\
# Brief — report per-region counts in the run summary

Two downstream jobs read the summary `tinyetl` prints at the end of a run:

- `reporting-daily` reads the summary once a day and charts the volume written.
- `alerting-hourly` reads it every hour and pages when the volume drops to zero.

What is wanted:

1. The summary reports how many rows were written per region, alongside the total it already
   reports as `row_count`.
2. The total keeps its current name and meaning, so neither reader has to change on the same day
   the field is added.
3. Whatever the two readers need to do to pick up the new field is stated, per reader.
""",
    },
    "author-single-change": {
        "shape": "authoring",
        "tokens": ["normalize_currency", "currency_code", "ValueError"],
        "brief": """\
# Brief — accept lower-case currency codes

One upstream feed emits `eur` rather than `EUR`, and every one of its rows is rejected today.

What is wanted:

1. `normalize_currency` accepts a `currency_code` in any letter case and returns the canonical
   upper-case form.
2. A code that is not a supported currency in any case still raises — the existing `ValueError`
   subclass, with the same message shape.

This is a single change to a single function. There is nothing else to it.
""",
    },
    "author-refactor-move": {
        "shape": "authoring",
        "holdout": True,
        "tokens": ["tinyetl/transforms/", "dedupe_orders", "normalize_currency"],
        "brief": """\
# Brief — split the transform module into a package

`tinyetl/transform.py` has grown three unrelated responsibilities and every new rule lands in the
same file.

What is wanted:

1. The module becomes a `tinyetl/transforms/` package: currency normalization, de-duplication and
   record shaping each get their own module inside it.
2. `normalize_currency`, `dedupe_orders` and `to_record` stay importable under the names callers
   use today — nothing outside the package changes its imports.
3. The test suite keeps passing unchanged.

This is a move, not a rewrite: no behaviour changes.
""",
    },
    "repair-bijection": {
        "shape": "repair",
        "defect": "its PR to section manifest does not line up with the numbered sections it "
        "claims to implement, and one of its concept rows names a module that is not there.",
        "tokens": ["--region", "KNOWN_REGIONS", "UnknownRegionError"],
        "floors": {
            # Set from the DEFECTIVE fixture, not from the repaired spec: the criterion asks
            # "did the arm delete content to go green?", so it must start TRUE and only fall.
            "min_sections": 5,
            "min_manifest_rows": 4,
            "required_headings": [
                "Concept → module map",
                "Numbered sections",
                "PR ↔ section manifest",
            ],
        },
    },
    "repair-ledger-drift": {
        "shape": "repair",
        "defect": "the fold ledger in its certification records rows against `path:line` "
        "positions that no longer hold the content the rows name, and one row is missing a cell.",
        "tokens": ["--region", "KNOWN_REGIONS", "UnknownRegionError"],
        "cert_policy": "preserved",
        "expected_cert": {"verdict": "CONDITIONAL-CERTIFY", "reviewer": "R. Okonkwo"},
        "floors": {
            "min_sections": 5,
            "min_manifest_rows": 5,
            "min_ledger_rows": 12,
            "required_headings": ["Numbered sections", "Pre-mortem certification"],
        },
    },
    "repair-enforcement-overclaim": {
        "shape": "repair",
        "holdout": True,
        "defect": "its prose claims invariants are enforced that its own enforcement-status "
        "table does not mark as enforced.",
        "tokens": ["retry_after_s", "schema_version", "migrate_v1_to_v2"],
        "floors": {
            "min_sections": 4,
            "min_manifest_rows": 4,
            "required_headings": ["Enforcement status", "Numbered sections"],
        },
    },
}

VERIFY_SHIM = '''\
"""Acceptance verifier for {task_id} (harness-side, scenario-blind).

Delegates to the bank-level ``keelgate_verify``, which scores every task with the same pinned
gate; ``profile.json`` beside this file names the criteria this task emits and the fixture
digests it protects. See that module for what this bank does and does not claim to measure.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import keelgate_verify` resolves

import keelgate_verify as kv  # noqa: E402

if __name__ == "__main__":
    sys.exit(kv.main(sys.argv, HERE / "profile.json"))
'''


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


KEPT = {"brief.md", "spec.md"}  # per-task material, not part of the shared tree


def _tree_files() -> list[Path]:
    return [
        p
        for p in sorted(TREE.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    ]


def sync_fixtures(dest: Path) -> None:
    """Mirror the shared tree into *dest*, pruning anything the tree no longer carries.

    Pruning matters: a byte-compiled cache or a since-deleted module left behind would enter
    `staged_sha256` and become part of what the integrity criterion protects.
    """
    wanted = {p.relative_to(TREE) for p in _tree_files()}
    for src in _tree_files():
        out = dest / src.relative_to(TREE)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
    for existing in sorted(dest.rglob("*"), reverse=True):
        rel = existing.relative_to(dest)
        if existing.is_file() and rel not in wanted and existing.name not in KEPT:
            existing.unlink()
        elif existing.is_dir() and not any(existing.iterdir()):
            existing.rmdir()


def build(task_id: str, spec: dict, force_briefs: bool) -> None:
    task_dir = BANK / task_id
    fixtures = task_dir / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    sync_fixtures(fixtures)

    if spec["shape"] == "authoring":
        brief = fixtures / "brief.md"
        if force_briefs or not brief.exists():
            brief.write_text(spec["brief"], encoding="utf-8", newline="\n")
        instruction = AUTHORING_INSTRUCTION
    else:
        (fixtures / "brief.md").unlink(missing_ok=True)
        instruction = REPAIR_INSTRUCTION.format(defect=spec["defect"])

    criteria = ["spec_written"] + SHARED + BEHAVIOUR + NOTE_ONLY + INTEGRITY
    if task_id == "author-single-change":
        # The correct answer declares `single-change`, which relaxes the structural trio to
        # absent-ok. Scoring criteria that the right answer is entitled to omit would manufacture
        # a null; the declaration itself becomes the criterion instead.
        criteria = [
            c
            for c in criteria
            if c
            not in (
                "numbered_sections_present",
                "manifest_is_bijection",
                "section_refs_resolve",
                "every_section_has_criterion",
            )
        ]
        criteria.append("kind_declared_single_change")
    if spec["shape"] == "repair":
        criteria += ["ledger_rows_anchor", "defect_not_masked"]
    if task_id == "repair-bijection":
        criteria.remove("ledger_rows_anchor")
    if task_id == "repair-enforcement-overclaim":
        criteria.remove("ledger_rows_anchor")
        criteria.append("enforcement_overclaims_absent")

    staged = {
        str(p.relative_to(fixtures)).replace("\\", "/"): digest(p)
        for p in sorted(fixtures.rglob("*"))
        if p.is_file() and p.name != "spec.md"
    }

    profile = {
        "shape": spec["shape"],
        "spec_path": "spec.md",
        "gate": ["spec_written", "gate_part_a_passes"],
        "brief_tokens": spec["tokens"],
        "cert_policy": spec.get("cert_policy", "absent"),
        "criteria": sorted(set(criteria)),
        "staged_sha256": staged,
    }
    if "expected_cert" in spec:
        profile["expected_cert"] = spec["expected_cert"]
    if "floors" in spec:
        profile["floors"] = spec["floors"]
    (task_dir / "profile.json").write_text(
        json.dumps(profile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    (task_dir / "verify.py").write_text(
        VERIFY_SHIM.format(task_id=task_id), encoding="utf-8", newline="\n"
    )

    task_toml = f'''id = "{task_id}"
instruction = """
{instruction}"""

[limits]
# Writing or repairing a design spec is a read-and-reason pass over a small staged tree, not a
# build. 900 s / 40 turns is set from the full-kit arm's shape (it has the most to read and the
# most to emit); the bare arm finishes well inside it.
trial_timeout_s = 900
max_turns = 40

[verify]
entry = "verify.py"
# The verifier imports a pinned copy of the readiness gate and runs it over the produced spec.
timeout_s = 120

[gate]
# The staged tree's own suite. Green on the untouched fixture, and it must stay green: no task in
# this bank asks any arm to touch the code, so a red gate means an arm edited the tree.
run = "python -m unittest discover -s tests -t ."
'''
    (task_dir / "task.toml").write_text(task_toml, encoding="utf-8", newline="\n")
    print(f"built {task_id}: {len(staged)} staged files, {len(profile['criteria'])} criteria")


if __name__ == "__main__":
    force = "--force-briefs" in sys.argv
    for tid, spec in TASKS.items():
        build(tid, spec, force)
