# treasuryutils-consumer plugin

Skills for engineers using `treasuryutils` in their own codebases:

- **`treasuryutils-usage`** — a decision matrix + module API references that
  route tasks to the correct module and prevent reimplementation of solved
  behaviour.
- **`setup-source-bindings`** — a guided workflow for setting up DataTools
  source bindings (rebinding primitive datasets to sources you can read). It
  orchestrates the deterministic bindings tooling — `doctor`,
  `scaffold-bindings`, and `validate-bindings` — and interacts with you for
  anything it cannot infer.
- **`auth-setup`** — a guided workflow for configuring authentication profiles.
  It drives the deterministic authenticator tooling — `doctor`,
  `scaffold-profile`, and `validate` (`python -m treasuryutils.authenticator`) —
  to diagnose which `auth_profile` your sources need, scaffold a `.env` skeleton,
  and validate it, while you supply the modality and the (never-echoed) secrets.
- **`dataset-creation`** — a guided workflow for authoring a NEW dataset
  contract. It drives the deterministic dataset tooling — `scaffold-dataset` and
  `validate-dataset` (`python -m treasuryutils.datatools`) — to scaffold a
  `DatasetConfig` skeleton per source driver and validate the columns/source/keys,
  while you supply the schema (the columns ARE the contract — never invented).

## Examples

The plugin ships runnable, self-checking example scripts under
[`examples/`](examples/README.md) — worked end-to-end patterns (CDI curve +
pricing, IFRS 9 ECL, portfolio risk/VaR, business-day cashflows, as-of
aggregation, and a fail-closed data-access walkthrough). The
`treasuryutils-usage` skill indexes them and points a task at the matching
example before writing new code.

## SessionStart hook

The plugin ships a `SessionStart` hook (`hooks/session-start-context.py`) that,
when a session begins, makes treasuryutils discoverable without forcing or
silently using it:

- **Announces** the consumer skills when the project **already depends on**
  treasuryutils, so a fresh agent — or a sub-agent that won't probe — prefers the
  library's public API over reimplementing solved behaviour.
- **Proposes** treasuryutils **once, neutrally** when the project does **not**
  depend on it but shows strong, specific treasury/finance signals it covers
  (e.g. CDI/SOFR, yield curves, business-day math, IFRS 9, VaR).

It inspects only local manifests/sources, installs and uses nothing on its own,
and never blocks a session. Silence the adoption suggestion with
`TREASURYUTILS_DISABLE_SUGGEST=1`. Sub-agents do not receive `SessionStart`
context, so the skills' trigger descriptions remain the primary lever for them.

## Testing feedback (opt-in, off by default)

While colleagues evaluate `treasuryutils`, the plugin can capture per-session
feedback automatically — but only when explicitly enabled. It is **off for
everyone by default**; nothing is written until a consumer opts in.

Enable it by setting one environment variable (persist it so every new session
picks it up):

```bash
# macOS / Linux — add to ~/.bashrc, ~/.zshrc, ...
export TREASURYUTILS_FEEDBACK=1

# Windows (PowerShell) — one-time; restart the terminal afterwards
setx TREASURYUTILS_FEEDBACK 1
```

When enabled, in any session that actually **uses** treasuryutils (runs it,
writes code against it, or invokes a consumer skill) the agent writes a short,
secret-free Markdown report to `~/Downloads/treasuryutils-feedback/` — one file
per session. Override the location with `TREASURYUTILS_FEEDBACK_DIR=/some/path`.

Two hooks implement it: a `SessionStart` hook primes the agent to write the
report before wrapping up, and a `Stop` hook is a safety net that asks for it
once if it is still missing at the end of a treasuryutils session. The report
never contains secrets or real data (`.env` values, tokens, IDs, customer or
financial data) — those are referred to by name only. **Disable** by clearing
the variable (`setx TREASURYUTILS_FEEDBACK ""` on Windows, or remove the export).

## Install

```text
/plugin marketplace add stone-payments/treasuryutils
/plugin install treasuryutils-consumer
```

## Karavela package install

```bash
uv add 'treasuryutils[all]' --index https://packages.stone.tech/repository/pypi-group/simple/
```
