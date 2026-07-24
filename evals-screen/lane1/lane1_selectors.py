"""Lane-1 offline selection-recall screen ($0; run with
`uv run --no-project --with sentence-transformers -- python lane1_selectors.py`).

Measures four selectors against the fresh sealed oblique holdout: does any beat the
lexical baseline at naming the right skill on paraphrased prompts?
- lexical       : content-word overlap between prompt and each skill's description
                  (a transparent proxy for the regex router's lexical matching).
- embedding     : dense cosine on the skill DESCRIPTIONS (2c).
- body-aware    : dense cosine on the skill BODIES (2g).
- enriched      : dense cosine on ENRICHED descriptions (1c/1e: symptoms + colloquial
                  + functional labels + not-for).
Reminder (E1): selection != incorporation. A winner here only earns a behavioral arm
if it beats the baseline by a wide margin.
"""

import json
import re
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

BASE = Path(__file__).resolve().parent
HOLDOUT = json.loads((BASE / "holdout.json").read_text(encoding="utf-8"))
PLUG = Path("C:/Users/grima/Documents/craft-collection/plugins")


def body(rel):
    return (PLUG / rel).read_text(encoding="utf-8")[:2000]


CAND = {
    "humblepowers:systematic-debugging": {
        "desc": "a reported defect; find and fix the underlying cause rather than the reported symptom, and check for other sites the same cause hits.",
        "body": "humblepowers/skills/systematic-debugging/SKILL.md",
        "enriched": "Use when a fix didn't hold, a bug came back in a new spot, or you keep patching symptoms and it keeps breaking elsewhere -- trace the failure to its root cause and check every site the same cause reaches. Not for writing a new feature from scratch.",
    },
    "engineering-discipline:data-engineering-discipline": {
        "desc": "data or pipeline correctness; verify the actual output against the input rather than infer from the code; watch for quiet row drops, duplication, and boundary miscounts.",
        "body": "engineering-discipline/skills/data-engineering-discipline/SKILL.md",
        "enriched": "Use when totals don't add up, rows seem to vanish or double, or aggregated numbers look plausible but are wrong -- verify the actual output values against the input, watching for quiet drops, duplication, and boundary miscounts. Not for pure UI or config edits.",
    },
    "humblepowers:verification-before-completion": {
        "desc": "proving a change works before calling it done; leave a check that would fail if the fix regressed.",
        "body": "humblepowers/skills/verification-before-completion/SKILL.md",
        "enriched": "Use when you're about to call something done but haven't confirmed it, or want to be sure an edit didn't quietly break existing behaviour -- prove it works and leave a check that catches a regression. Not for the initial design.",
    },
    "humblepowers:test-driven-development": {
        "desc": "writing new production code against a test seen failing first (red-green-refactor).",
        "body": "humblepowers/skills/test-driven-development/SKILL.md",
        "enriched": "Use when starting brand-new code and you want to pin down the expected checks first and let them drive the implementation (red-green-refactor). Not for debugging existing code.",
    },
    "humblepowers:brainstorming": {
        "desc": "turning a vague or bundled request into an agreed design before implementation.",
        "body": "humblepowers/skills/brainstorming/SKILL.md",
        "enriched": "Use when a request is vague or bundles several things and you need to shape an agreed design before writing code. Not for a well-specified task.",
    },
    "humblepowers:receiving-code-review": {
        "desc": "evaluating incoming review feedback on its merits.",
        "body": "humblepowers/skills/receiving-code-review/SKILL.md",
        "enriched": "Use when a reviewer left feedback and you need to weigh which points hold up on their merits. Not for giving review to others.",
    },
    "none": {
        "desc": "a routine, self-contained edit that needs no special engineering discipline.",
        "body": None,
        "enriched": "A routine, self-contained edit -- rename, docstring, constant bump, typo fix, reformat -- that needs no engineering discipline; just make the minimal correct change.",
    },
}

LABELS = list(CAND)
model = SentenceTransformer("all-MiniLM-L6-v2")

VIEWS = {
    "embedding": {l: CAND[l]["desc"] for l in LABELS},
    "body-aware": {
        l: (body(CAND[l]["body"]) if CAND[l]["body"] else CAND[l]["desc"]) for l in LABELS
    },
    "enriched": {l: CAND[l]["enriched"] for l in LABELS},
}
ENC = {v: {l: model.encode(t[l]) for l in LABELS} for v, t in VIEWS.items()}

STOP = set(
    "the a an of to for and or in on is it this that with your you i be as at from by "
    "do does did if not so but out up down when what which want would like some few my "
    "me they them their there here into over after before now still keep every each".split()
)


def toks(s):
    return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 2}


def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def rank_lexical(prompt):
    pt = toks(prompt)
    scored = [(l, len(pt & toks(CAND[l]["desc"]))) for l in LABELS]
    return [l for l, _ in sorted(scored, key=lambda x: -x[1])]


def rank_dense(prompt, view):
    pe = model.encode(prompt)
    scored = [(l, cosine(pe, ENC[view][l])) for l in LABELS]
    return [l for l, _ in sorted(scored, key=lambda x: -x[1])]


SELECTORS = {
    "lexical": lambda p: rank_lexical(p),
    "embedding": lambda p: rank_dense(p, "embedding"),
    "body-aware": lambda p: rank_dense(p, "body-aware"),
    "enriched": lambda p: rank_dense(p, "enriched"),
}


def main():
    items = HOLDOUT["items"]
    n = len(items)
    # non-null items measure real selection; null items measure abstention (top-1 == none)
    non_null = [it for it in items if it["skill"] != "none"]
    nulls = [it for it in items if it["skill"] == "none"]
    print(f"n={n}  ({len(non_null)} skill-labeled, {len(nulls)} none)\n")
    print(f"{'selector':<12} {'recall@1':>9} {'recall@2':>9} {'none@1':>8}")
    for name, fn in SELECTORS.items():
        r1 = sum(fn(it["prompt"])[0] == it["skill"] for it in non_null)
        r2 = sum(it["skill"] in fn(it["prompt"])[:2] for it in non_null)
        none1 = sum(fn(it["prompt"])[0] == "none" for it in nulls)
        m = len(non_null)
        print(
            f"{name:<12} {r1}/{m}={r1 / m:.2f}  {r2}/{m}={r2 / m:.2f}  {none1}/{len(nulls)}={none1 / len(nulls):.2f}"
        )


if __name__ == "__main__":
    main()
