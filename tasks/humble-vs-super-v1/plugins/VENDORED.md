# Vendored plugins — humble-vs-super-v1

Pinned copies of the four plugins mounted by the arm scenarios.  These are
committed so that all arms hash deterministically (§2) and the vendored content
is immutable across the life of the analysis.

## humblepowers@0.3.1

| Field | Value |
|---|---|
| Name | humblepowers |
| Version | 0.3.1 |
| Source repo | https://github.com/grimaldost/craft-collection |
| Source commit | c9bd55e1bc54d0c63d109100c153554abc220740 (craft-collection tag 0.3.1) |
| Cache source | `~/.claude/plugins/cache/craft-collection/humblepowers/0.3.1` |
| Content copied | `.claude-plugin/`, `skills/`, `hooks/` |

The **treatment arm** — the humble process-discipline plugin being evaluated.

## superpowers@6fd4507

| Field | Value |
|---|---|
| Name | superpowers |
| Version | 5.1.0 |
| Source repo | https://github.com/obra/superpowers |
| Pinned commit | 6fd4507659784c351abbd2bc264c7162cfd386dc |
| Cache source | `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0` |
| Content copied | `.claude-plugin/`, `skills/`, `hooks/` |

The **contrast arm** — obra's superpowers plugin at the commit spike-validated
in the spec (§ Spike validation, 2026-06-14).  The cache was cloned from
`github.com/obra/superpowers` at this exact commit; confirmed via
`.git/refs/heads/main` in the cache.

## engineering-discipline

| Field | Value |
|---|---|
| Name | engineering-discipline |
| Version | 0.1.2 |
| Source repo | https://github.com/grimaldost/craft-collection |
| Source commit | 08d7ad9f672827dc949a7db930cf237112e43aef |
| Cache source | `~/.claude/plugins/cache/craft-collection/engineering-discipline/0.1.2` |
| Content copied | `.claude-plugin/`, `skills/`, `hooks/` |

Part of the **held-constant stack** mounted identically in both `stack-humble`
and `stack-super` arms for common-mode cancellation (§1/§8).

## session-workflow

| Field | Value |
|---|---|
| Name | session-workflow |
| Version | 0.2.2 |
| Source repo | https://github.com/grimaldost/craft-collection |
| Source commit | c9bd55e1bc54d0c63d109100c153554abc220740 |
| Cache source | `~/.claude/plugins/cache/craft-collection/session-workflow/0.2.2` |
| Content copied | `.claude-plugin/`, `skills/`, `hooks/` |

Part of the **held-constant stack** mounted identically in both `stack-humble`
and `stack-super` arms for common-mode cancellation (§1/§8).
