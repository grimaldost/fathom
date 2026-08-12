# Vendored plugins — humble-vs-super-v5

Pinned copies of the plugins mounted by the v5 arm scenarios. They are vendored (rather
than referenced from a live install) so every arm hashes deterministically and the
measured content is immutable for the life of the analysis: `config_hash` includes a
`tree_sha` over every file under each mounted dir, so a live plugin that ships a release
mid-matrix would silently fork the arm.

The v5 refresh is deliberately **one-axis**: only the treatment plugin (`humblepowers`)
moves to merged state. The held-constant stack stays at the versions v1/v2 pinned, so the
sole craft-collection delta between v2 and v5 is the treatment. See `../V5_NOTES.md` §
"What changed, and what deliberately did not".

## humblepowers@0.9.1 — treatment

| Field | Value |
|---|---|
| Name / version | humblepowers 0.9.1 |
| Source repo | https://github.com/grimaldost/craft-collection |
| Source | working tree of `craft-collection` on `main` at commit `b7b0097` (`feat(choosing-models): calibration pass on the 2026-08-11 model-tier evidence`) |
| Path copied from | `plugins/humblepowers/` |
| Content copied | `.claude-plugin/`, `skills/`, `hooks/` |
| Excluded | `README.md`, `LICENSE`, `CHANGELOG.md` (not loaded by Claude Code, so they are not part of the treatment); `__pycache__/`, `.pytest_cache/` (build residue — and `.pytest_cache` is **not** on fathom's tree-hash skiplist, so leaving it in would fork `config_hash` on a stray cache write) |
| Normalised | `skills/choosing-models/models.toml` was copied with CRLF endings and rewritten to LF, so the working tree matches the bytes git stores under `.gitattributes` (`*.toml text eol=lf`). Left as CRLF it would have flipped to LF on the next checkout of this file and forked `tree_sha` — hence `config_hash` and the resume key — in the middle of an analysis. No other committed vendored file carries CRLF. |

This is the **merged** plugin body, not an installed-cache snapshot: the source of truth
is the repo working tree on `main`, matching the practice established by the 2026-08-11
`skill-pyeng-v1` merged-content re-run (the installed cache trails the repo).

Skill inventory vs the 0.4.0 tree v2 measured: **superset**, nothing removed or renamed.

| skill | 0.4.0 (v2) | 0.9.1 (v5) |
|---|---|---|
| `brainstorming` | yes | yes |
| `choosing-tools` | yes | yes (+ `scripts/router.py`, `router_rules.json`, tests) |
| `planned-execution` | yes | yes (+ `subagent-prompts.md`) |
| `receiving-code-review` | yes | yes |
| `skill-authoring` | yes | yes |
| `systematic-debugging` | yes | yes (+ 3 reference files) |
| `test-driven-development` | yes | yes (+ `testing-anti-patterns.md`) |
| `verification-before-completion` | yes | yes |
| `choosing-models` | — | **new** |
| `refresh-models` | — | **new** |

## superpowers@6fd4507 — contrast

| Field | Value |
|---|---|
| Name / version | superpowers 5.1.0 |
| Source repo | https://github.com/obra/superpowers |
| Pinned commit | `6fd4507659784c351abbd2bc264c7162cfd386dc` |
| License | MIT (per `.claude-plugin/plugin.json`) |
| Content copied | `.claude-plugin/`, `skills/`, `hooks/` — 52 files |
| Provenance of this copy | byte-identical (verified by `diff -r`) to the v1 snapshot at `tasks/humble-vs-super-v1/plugins/superpowers@6fd4507`, which is the snapshot every published humble-vs-super verdict (v1–v4) was measured against |
| Integrity manifest | `superpowers-6fd4507.sha256` (tracked; 52 sha256 lines) |

**This directory is deliberately NOT committed.** The repo's `.gitignore` carries
`tasks/*/plugins/superpowers@*/` — "vendored THIRD-PARTY plugin snapshots, excluded
pending a submodule/pin decision (2026-07-01)". v5 keeps that decision rather than
adding a per-bank negation: overturning a repo-wide third-party-vendoring policy is not
a measurement bank's call, and a negation for one bank would leave the policy
inconsistent across v1 and v5. The licence permits vendoring; the standing pin decision
is what is being respected.

The cost of that choice is that **a fresh clone cannot reproduce the contrast arm
without re-vendoring**, and fathom only *warns* on a missing mount — a missing tree
degrades `stack-super` into something close to `stack-humble`-minus-humblepowers and
manufactures a null. Four compensating controls carry the risk:

1. `superpowers-6fd4507.sha256` — re-vendor, then `sha256sum -c` from inside the
   snapshot dir; any drift from the measured bytes is caught.
2. `tests/test_humble_super_v5_mounts.py` — every mount declared by a v5 scenario must
   resolve to a real plugin dir; the third-party snapshot is checked against the
   manifest when present and reported as a hard `re-vendor first` skip when absent.
3. `uv run fathom verify-arming --scenarios-dir scenarios/humble-vs-super-v5` — the live
   gate. `EXIT_UNARMED` is the stop that catches an arm that did not actually reach the
   spawn. It is the only control that observes the real spawn; the other three are
   static.
4. `V5_NOTES.md` states the re-vendoring step in the run recipe, before the gates.

### Re-vendoring recipe

```sh
git clone -c core.autocrlf=true https://github.com/obra/superpowers /tmp/superpowers
git -C /tmp/superpowers checkout 6fd4507659784c351abbd2bc264c7162cfd386dc
mkdir -p tasks/humble-vs-super-v5/plugins/superpowers@6fd4507
cp -r /tmp/superpowers/.claude-plugin /tmp/superpowers/skills /tmp/superpowers/hooks \
      tasks/humble-vs-super-v5/plugins/superpowers@6fd4507/
cd tasks/humble-vs-super-v5/plugins/superpowers@6fd4507 && sha256sum -c ../superpowers-6fd4507.sha256
```

**Line endings are part of the pin.** The measured snapshot is a Windows checkout: 11
files whose extensions the repo's `.gitattributes` does not force to LF (`.cmd`, `.sh`,
`.js`, `.cjs`, `.ts`, `.html`, `.dot`, and the extensionless `hooks/session-start`) carry
CRLF, and the manifest records those bytes. `-c core.autocrlf=true` on the clone
reproduces them. A re-vendor that differs *only* in line endings changes no skill text
the model reads — every `SKILL.md` is LF on both sides — but it does change fathom's
`tree_sha`, and therefore `config_hash` and the resume key. So a manifest mismatch must
be fixed rather than waved through: left alone it would split one arm across two
`config_hash`es mid-matrix, and the resume would re-spend instead of continuing.

## engineering-discipline 0.1.2 — held-constant stack

| Field | Value |
|---|---|
| Name / version | engineering-discipline 0.1.2 |
| Source repo | https://github.com/grimaldost/craft-collection |
| Source commit | `08d7ad9f672827dc949a7db930cf237112e43aef` |
| Provenance of this copy | byte-identical to `tasks/humble-vs-super-v2/plugins/engineering-discipline` |

## session-workflow 0.2.2 — held-constant stack

| Field | Value |
|---|---|
| Name / version | session-workflow 0.2.2 |
| Source repo | https://github.com/grimaldost/craft-collection |
| Source commit | `c9bd55e1bc54d0c63d109100c153554abc220740` |
| Provenance of this copy | byte-identical to `tasks/humble-vs-super-v2/plugins/session-workflow` |

Both are mounted **identically** in `stack-humble` and `stack-super` for common-mode
cancellation, and in neither in `bare`. They are pinned, not refreshed: on `main` they
now read 0.4.0 and 0.21.0 respectively, and moving them would change the measurement on
a second axis at the same time as the treatment. The consequence — v5 measures
humblepowers 0.9.1 inside a 2026-06-era stack, not inside the full merged toolkit — is
recorded as a stated limitation in `../V5_NOTES.md`, not silently absorbed.
