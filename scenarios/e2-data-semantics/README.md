# Arms for `e2-data-semantics`

Run them with `--scenarios-dir scenarios/e2-data-semantics` — `fathom run` globs
a scenarios dir non-recursively, and omitting the flag silently runs the wrong
arms.

| Arm | Treatment | Question it answers |
|---|---|---|
| `bare` | none | the never-run baseline: does the surface beat no surface at all |
| `skill-current` | `[context] inject = assets/skill-current.md` | does the surface as it stands beat bare |
| `skill-vnext` | `[context] inject = assets/skill-vnext.md` | does the revised surface beat the shipped one, and does it still beat bare |

Arms differ in **one** thing: the injected body. Model, effort, strategy, tool
allow-list and limits are identical, so nothing but the surface can explain a
difference. `skill-current` is byte-identical to the base commit the revision
was written on top of (verified: `git show 07fea4f:<skill path>` diffs clean
against the pinned asset), so `skill-current` → `skill-vnext` is exactly the
revision series and nothing else.

## Asset provenance — `assets/skill-current.md`

Extracted verbatim (frontmatter included, no edits) from the published skill:

| | |
|---|---|
| Repository | `craft-collection` |
| Path | `plugins/engineering-discipline/skills/data-engineering-discipline/SKILL.md` |
| Plugin version | `engineering-discipline` 0.4.0 |
| Blob sha | `e836366d3438e676044f6923ea8267d4dfd2b73b` |
| Last commit touching the skill dir | `d1d5d620d539a3bd1fee1b267086a298021b01bb` (2026-07-14) |
| Extracted at | `main` = `b3772ea1a08ae809706c54b29e314c2a016c8b3b` |
| Asset content sha256 | `00d05bb342b8350fc74c3bb8d58818a0f3a1922900f165b3967583d517928acf` |
| Size | 19,721 bytes, 362 lines, LF |

```sh
git -C <craft-collection> show e836366d3438e676044f6923ea8267d4dfd2b73b \
    > scenarios/e2-data-semantics/assets/skill-current.md
```

## Asset provenance — `assets/skill-vnext.md`

Extracted verbatim (frontmatter included, no edits) from the revised skill, by
the same recipe:

| | |
|---|---|
| Repository | `craft-collection` |
| Path | `plugins/engineering-discipline/skills/data-engineering-discipline/SKILL.md` |
| Plugin version | `engineering-discipline` 0.5.0 |
| Blob sha | `9541aff4d0647083227131f6236b480f29384bb6` |
| Extracted at | `feat/data-discipline-vnext` = `a339aaaba369859f78535e3c966d1d92c5109efd` (branched off `07fea4f`) |
| Asset content sha256 | `68ae1837f248554fd7cb873b0b8a5d792950b28914fc84773bdd98ab4275620d` |
| Size | 16,511 bytes, 303 lines, LF |

```sh
git -C <craft-collection> show 9541aff4d0647083227131f6236b480f29384bb6 \
    > scenarios/e2-data-semantics/assets/skill-vnext.md
```

The revision is unmerged at extraction time. That is deliberate: the point of
the arm is to price the change *before* it ships, so the pin is a branch tip and
a blob sha rather than a released tag. If the branch is rebased or amended, the
blob sha above is what identifies what was measured — not the branch name.

**Why a snapshot rather than a mounted checkout.** `[plugins] mount` takes a live
directory and its tree hash enters `config_hash`, so a commit landing in a shared
checkout mid-matrix changes the hash and invalidates resume. That is not
hypothetical here: the source repo's `main` advanced during authoring (07fea4f →
b3772ea) while this bank was being written. The skill blob was byte-identical
across both tips, which is why the pin is stated as a blob sha rather than a
branch. Pinning the content into this repo makes the treatment reproducible from
this repo alone.

## Known limitations of this instrument

- **The injected body carries pointers to files the workspace does not have** —
  its `references/*.md` and `scripts/*.py` are not staged into the task
  workspace. This is the same shape as the reference skill bank
  (`scenarios/skill-pyeng/assets/python-engineering.md`, which also injects a
  SKILL.md verbatim with live `references/` pointers), so it is a constant of the
  instrument rather than a difference between arms — but it means what is
  measured is the body's effect on behaviour, not the effect of the body plus its
  reachable references and runnable checks. A doctrine that presupposes a tool
  the agent does not have has been measured elsewhere to cost more than no
  doctrine; that cost, if present, lands on every injected arm equally.
- **Injection is not activation.** Appending the body to the system prompt
  removes the trigger question entirely. This bank measures whether the content
  changes what the agent does, not whether the description fires. Trigger recall
  and specificity are a separate instrument and are not bought here.
