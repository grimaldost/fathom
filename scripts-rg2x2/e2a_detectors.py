#!/usr/bin/env python3
"""E2a: offline measurement of action-stream discipline detectors.

Read-only measurement of four candidate deterministic detectors over recorded
Claude Code session transcripts. Each detector reads the *action stream* (the
sequence of tool_use events in a session) and flags a session where a named
process discipline plausibly should have been in play but may have been absent.

Hypothesis (Band C): needs that emerge mid-task surface in the agent's actions
even when absent from the user's prompt, so cheap deterministic detectors over
the action stream can catch when a discipline should engage. This script measures
each detector's hit/noise rate against real sessions before any runtime hook.

Corpus: Claude Code transcripts at <projects_dir>/*/*.jsonl (NDJSON, one file per
session). The glob is one level deep, which excludes nested subagent transcripts
(<project>/<session>/subagents/*.jsonl) by construction.

Usage:
    python e2a_detectors.py <projects_dir>

stdlib only, read-only. Nothing is written or mutated.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
import time
from collections import defaultdict

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
MAX_SESSIONS = 30  # most-recent N transcript files by mtime
MAX_FILE_BYTES = 20 * 1024 * 1024  # skip files larger than this
MAX_SAMPLES = 5  # sample hits printed per detector

# Editing tools whose input carries a file_path we care about.
EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}
BASH_TOOLS = {"Bash", "PowerShell"}

# Test/build command markers (per detector spec). Substring match on the
# lowercased command. 'test' and 'build' are deliberately broad per spec.
TESTBUILD_MARKERS = (
    "pytest",
    "npm test",
    "cargo test",
    "go test",
    "ruff",
    "mypy",
    "test",
    "build",
)

# Markers in a tool_result that indicate a command run failed.
FAIL_MARKERS = ("traceback", "failed", "error", "exit code")

# Fix-intent language in a first user prompt (EN + PT-BR).
FIX_INTENT = ("fix", "bug", "broken", "wrong", "falha", "corrigir", "quebrado", "errado")

# Source-file extensions (for bugfix-no-test).
SOURCE_EXTS = (
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".kt",
    ".swift",
    ".php",
    ".scala",
)

# Schema/migration territory (for schema-paths).
SCHEMA_MARKERS = ("/migrations/", "/alembic/", ".sql", "schema", "models.py", "dbt/")

_CD_PREFIX = re.compile(r'^\s*cd\s+(?:"[^"]*"|\'[^\']*\'|\S+)\s*(?:&&|;)\s*', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def norm_path(p: str) -> str:
    """Lowercase and normalize path separators to '/'."""
    return p.replace("\\", "/").lower()


def result_text(block) -> str:
    """Extract text from a tool_result content field (str or list-of-blocks)."""
    c = block.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for x in c:
            if isinstance(x, dict) and isinstance(x.get("text"), str):
                parts.append(x["text"])
        return " ".join(parts)
    return ""


def extract_user_text(content) -> str:
    """Pull plain text out of a user record's content (str or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str):
                parts.append(b["text"])
        return " ".join(parts)
    return ""


def looks_like_wrapper(text: str) -> bool:
    """True if a user text is a harness/command wrapper rather than a real prompt."""
    t = text.lstrip()
    return t.startswith(
        (
            "<command-name>",
            "<command-message>",
            "<local-command-stdout>",
            "<bash-input>",
            "<bash-stdout>",
            "Caveat:",
            "[Request interrupted",
        )
    )


def cmd_signature(command: str) -> str:
    """Normalize a shell command to its first-5-token signature.

    Strips a leading `cd <dir> && ` / `cd <dir> ; ` prefix, replaces path-like
    tokens with their basename, collapses whitespace, and keeps the first 5
    tokens. Used to group repeated invocations of the "same" command.
    """
    c = _CD_PREFIX.sub("", command).strip().lower()
    toks = c.split()
    out = []
    for tok in toks[:5]:
        t = tok.strip("\"'")
        if "/" in t or "\\" in t:
            t = re.split(r"[\\/]", t)[-1] or t
        out.append(t)
    return " ".join(out)


def is_testbuild(command: str) -> bool:
    lc = command.lower()
    return any(m in lc for m in TESTBUILD_MARKERS)


def parse_session(path: str):
    """Parse one transcript into an ordered event stream + first prompt.

    Returns dict with:
      tool_uses: list of (order, name, input_dict, tool_use_id)
      results:   {tool_use_id: result_text}
      first_prompt: str
      n_records, n_bad_lines
    """
    tool_uses = []
    results = {}
    first_prompt = None
    order = 0
    n_records = 0
    n_bad = 0

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                n_bad += 1
                continue
            if not isinstance(rec, dict):
                continue
            n_records += 1
            rtype = rec.get("type")
            msg = rec.get("message")
            if rtype == "assistant" and isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "tool_use":
                            name = b.get("name")
                            inp = b.get("input")
                            inp = inp if isinstance(inp, dict) else {}
                            tool_uses.append((order, name, inp, b.get("id")))
                            order += 1
            elif rtype == "user" and isinstance(msg, dict):
                content = msg.get("content")
                # collect any tool_result blocks
                if isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "tool_result":
                            results[b.get("tool_use_id")] = result_text(b)
                # first genuine user prompt: skip sidechain/meta/wrapper/tool-result-only
                if first_prompt is None and not rec.get("isSidechain") and not rec.get("isMeta"):
                    txt = extract_user_text(content)
                    if txt and not looks_like_wrapper(txt):
                        first_prompt = txt

    return {
        "tool_uses": tool_uses,
        "results": results,
        "first_prompt": first_prompt or "",
        "n_records": n_records,
        "n_bad": n_bad,
    }


# ---------------------------------------------------------------------------
# Detectors
# Each returns (fired: bool, samples: list[str]) for the session.
# ---------------------------------------------------------------------------
def det_repeat_failing_cmd(sess):
    """>=3 test/build commands sharing a signature; failing (marker) >=3, or
    (no result markers) same command repeated >=4 as proxy."""
    groups = defaultdict(list)  # signature -> list of (command, tool_use_id)
    for _o, name, inp, tuid in sess["tool_uses"]:
        if name not in BASH_TOOLS:
            continue
        cmd = inp.get("command")
        if not isinstance(cmd, str) or not is_testbuild(cmd):
            continue
        groups[cmd_signature(cmd)].append((cmd, tuid))

    samples = []
    fired = False
    for sig, items in groups.items():
        if len(items) < 3:
            continue
        failing = 0
        have_results = 0
        for _cmd, tuid in items:
            res = sess["results"].get(tuid)
            if res:
                have_results += 1
                rl = res.lower()
                if any(m in rl for m in FAIL_MARKERS):
                    failing += 1
        strong = failing >= 3
        proxy = (have_results == 0 or failing < 3) and len(items) >= 4
        if strong or proxy:
            fired = True
            basis = f"failing={failing}" if strong else f"repeat-proxy n={len(items)}"
            samples.append(f"sig='{sig}' n={len(items)} {basis} :: {items[0][0][:90]}")
    return fired, samples


def det_schema_paths(sess):
    """Edit/Write to migration/schema territory."""
    samples = []
    fired = False
    for _o, name, inp, _tuid in sess["tool_uses"]:
        if name not in EDIT_TOOLS:
            continue
        fp = inp.get("file_path")
        if not isinstance(fp, str):
            continue
        n = norm_path(fp)
        if any(m in n for m in SCHEMA_MARKERS):
            fired = True
            samples.append(f"{name} -> {fp}")
    return fired, samples


def det_bugfix_no_test(sess):
    """First prompt has fix-intent AND >=1 source edit AND ZERO test edits."""
    prompt = sess["first_prompt"].lower()
    if not any(k in prompt for k in FIX_INTENT):
        return False, []

    src_edits = []
    test_edits = 0
    for _o, name, inp, _tuid in sess["tool_uses"]:
        if name not in EDIT_TOOLS:
            continue
        fp = inp.get("file_path")
        if not isinstance(fp, str):
            continue
        n = norm_path(fp)
        base = n.rsplit("/", 1)[-1]
        is_test = (
            "/tests/" in n
            or "/test/" in n
            or base.startswith("test_")
            or "_test." in base
            or ".spec." in base
            or ".test." in base
        )
        if is_test:
            test_edits += 1
        elif any(n.endswith(ext) for ext in SOURCE_EXTS):
            src_edits.append(fp)

    if src_edits and test_edits == 0:
        snippet = re.sub(r"\s+", " ", sess["first_prompt"]).strip()[:70]
        samples = [f"prompt='{snippet}...' src_edits={len(src_edits)} e.g. {src_edits[0]}"]
        return True, samples
    return False, []


def det_ship_no_verify(sess):
    """git commit/push with NO test/build command earlier in the session."""
    first_testbuild_order = None
    commit_events = []  # (order, command)
    for o, name, inp, _tuid in sess["tool_uses"]:
        if name not in BASH_TOOLS:
            continue
        cmd = inp.get("command")
        if not isinstance(cmd, str):
            continue
        lc = cmd.lower()
        if is_testbuild(cmd) and first_testbuild_order is None:
            first_testbuild_order = o
        if "git commit" in lc or "git push" in lc:
            commit_events.append((o, cmd))

    samples = []
    fired = False
    for o, cmd in commit_events:
        if first_testbuild_order is None or o < first_testbuild_order:
            fired = True
            samples.append(f"@order {o}: {cmd[:100]}")
    return fired, samples


DETECTORS = [
    ("repeat-failing-cmd", "systematic-debugging", det_repeat_failing_cmd),
    ("schema-paths", "data-engineering-discipline", det_schema_paths),
    ("bugfix-no-test", "test-driven-development", det_bugfix_no_test),
    ("ship-no-verify", "verification-before-completion", det_ship_no_verify),
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv):
    if len(argv) < 2:
        print("usage: python e2a_detectors.py <projects_dir>", file=sys.stderr)
        return 2
    projects_dir = argv[1]

    all_files = glob.glob(os.path.join(projects_dir, "*", "*.jsonl"))
    all_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)

    selected = []
    skipped_big = 0
    for p in all_files:
        if len(selected) >= MAX_SESSIONS:
            break
        try:
            if os.path.getsize(p) > MAX_FILE_BYTES:
                skipped_big += 1
                continue
        except OSError:
            continue
        selected.append(p)

    t0 = time.perf_counter()
    parsed = []
    skipped_empty = 0
    total_tool_use = 0
    total_bad_lines = 0
    for p in selected:
        try:
            sess = parse_session(p)
        except Exception as e:  # never fatal
            skipped_empty += 1
            print(f"  [parse error] {os.path.basename(p)}: {e}", file=sys.stderr)
            continue
        if sess["n_records"] == 0:
            skipped_empty += 1
            continue
        sess["stem"] = os.path.splitext(os.path.basename(p))[0]
        sess["project"] = os.path.basename(os.path.dirname(p))
        parsed.append(sess)
        total_tool_use += len(sess["tool_uses"])
        total_bad_lines += sess["n_bad"]
    wall = time.perf_counter() - t0

    # Run detectors
    fire_sessions = {name: 0 for name, _d, _f in DETECTORS}
    fire_count = {name: 0 for name, _d, _f in DETECTORS}
    samples = {name: [] for name, _d, _f in DETECTORS}
    for sess in parsed:
        for name, _disc, fn in DETECTORS:
            fired, samps = fn(sess)
            if fired:
                fire_sessions[name] += 1
                fire_count[name] += len(samps) if samps else 1
                for s in samps:
                    if len(samples[name]) < MAX_SAMPLES:
                        samples[name].append((sess["stem"], sess["project"], s))

    # -------------------------------------------------------------------
    # Report
    # -------------------------------------------------------------------
    n = len(parsed)
    print("=" * 74)
    print("E2a ACTION-STREAM DETECTOR MEASUREMENT")
    print("=" * 74)
    print("\n[CORPUS]")
    print(f"  transcript files matched (glob */*.jsonl): {len(all_files)}")
    print(f"  selected (most-recent, <=20MB):           {len(selected)}")
    print(f"  skipped (>20MB):                          {skipped_big}")
    print(f"  skipped (empty/unparseable):              {skipped_empty}")
    print(f"  sessions parsed:                          {n}")
    print(f"  total tool_use events:                    {total_tool_use}")
    print(f"  bad (unparseable) NDJSON lines:           {total_bad_lines}")
    print(
        f"  full-file parse wall-time:                {wall:.3f}s"
        f"  ({wall / n * 1000:.1f} ms/session avg)"
        if n
        else ""
    )

    print("\n[PER-DETECTOR SUMMARY]  (sessions fired / total; total fire count)")
    for name, disc, _f in DETECTORS:
        print(
            f"  {name:20s} -> {disc:32s} "
            f"fired {fire_sessions[name]:2d}/{n}  fires={fire_count[name]}"
        )

    print("\n[SAMPLE HITS]")
    for name, disc, _f in DETECTORS:
        print(f"\n  ## {name}  ({disc})")
        if not samples[name]:
            print("     (no fires)")
            continue
        for stem, proj, s in samples[name]:
            print(f"     [{proj[:28]} | {stem[:12]}] {s}")

    print("\n" + "=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
