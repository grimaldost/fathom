# Implementation plan — fathom skill-eval (python-engineering), Phase 1

**Goal:** add per-scenario system-prompt injection to fathom and a legacy-modernization bank so a
with/without effectiveness eval of the `python-engineering` skill runs verifier-only end to end.

**Architecture:** the fathom spine is unchanged. One new capability — a `[context] inject = <file>`
scenario field whose body is appended to the spawn's system prompt via `--append-system-prompt-file`,
content-hashed into `config_hash`. A new bank `skill-pyeng-v1` (one modernize task) with a verifier
that ports the skill's own `doctor.audit()` (5 compliance criteria) plus a layout-agnostic
behavior-preserved check. Three arms (`bare`, `generic-nudge`, `pyeng-skill`) in an isolated
`scenarios/skill-pyeng/` dir. `report.py` gains a per-criterion table so compliance and correctness
don't blend.

**Tech stack:** Python 3.12, stdlib-only core, `unittest`/`pytest`, `ruff`, `uv`. Spawn boundary
injected as a stub in tests (no real spawns outside `fathom smoke`).

**Execution mode:** planned-execution loop — per task, a fresh implementer subagent, then
spec-compliance review, then code-quality review, re-reviewing after each fix.

**Gate commands (every task ends green on these):**
- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest -q`

---

## File map

| File | Create/modify | Responsibility |
|---|---|---|
| `src/fathom/scenario.py` | modify | `ContextConfig`; parse `[context] inject`; content-hash into `config_hash` |
| `src/fathom/adapters/claude_cli.py` | modify | `--append-system-prompt-file` in `build_command` + `ClaudeCliRunner` |
| `src/fathom/cli.py` | modify | factory wires inject path; warn on unarmed treatment |
| `src/fathom/smoke.py` | modify | `injection_file_of(argv)` pure helper (K7) |
| `src/fathom/report.py` | modify | per-criterion pass-rate table |
| `tests/test_scenario.py` | modify | `TestContextInjection` |
| `tests/test_adapter_claude_cli.py` | modify | append-flag build + execute argv tests |
| `tests/test_cli.py` | modify | factory passes inject; warns on missing file |
| `tests/test_smoke_logic.py` | modify | `injection_file_of` tests |
| `tests/test_report.py` | modify | per-criterion table assertions + golden regen |
| `tests/test_bank_skill_pyeng_v1.py` | create | bank loads; verifier flips both ways |
| `tasks/skill-pyeng-v1/bank.toml` | create | bank manifest |
| `tasks/skill-pyeng-v1/modernize-timeflow/task.toml` | create | task definition |
| `tasks/skill-pyeng-v1/modernize-timeflow/fixtures/**` | create | flat-layout legacy project (~0/5) |
| `tasks/skill-pyeng-v1/modernize-timeflow/verify.py` | create | ported doctor + behavior check |
| `scenarios/skill-pyeng/{bare,generic-nudge,pyeng-skill}.toml` | create | the three arms |
| `scenarios/skill-pyeng/assets/{python-engineering,generic-nudge}.md` | create | injected treatment bodies |

---

## T1 — scenario `context.inject` + content-hash

**Files:** `src/fathom/scenario.py`, `tests/test_scenario.py`.
**Acceptance:** a scenario with no `[context]` and one with `[context]` but no `inject` hash
identically to today's `bare` (the committed series-engine bank's ledger keys do not shift); setting
`inject` changes the hash; two different injected bodies produce different hashes; `load_scenario`
resolves a relative `inject` against the scenario file's directory.

**Step 1.1 — failing tests.** Add to `tests/test_scenario.py` (after `TestToolAllowlists`):

```python
class TestContextInjection(unittest.TestCase):
    """The [context] inject field: a treatment scenario appends a file's body to
    the spawn's system prompt. Absent inject == no context (hash-stable vs the
    committed series-engine ledger); the *content* (sha256), not the path, enters the
    hash so editing the body forks history but moving the file does not."""

    def _write(self, tmp: Path, context_block: str) -> Path:
        p = tmp / "s.toml"
        p.write_text(
            'name = "s"\n'
            'adapter = "claude-cli"\n'
            'model = "m"\n'
            'strategy = "single-session"\n'
            'effort = "high"\n'
            '[tools]\nsource = "none"\nallowed = ["Read"]\n'
            f"{context_block}\n",
            encoding="utf-8",
        )
        return p

    def test_absent_and_no_inject_hash_identically(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            r = StubResolver()
            absent = resolve_scenario(load_scenario(self._write(tmp, "")), r)
            empty_ctx = resolve_scenario(load_scenario(self._write(tmp, "[context]")), r)
            self.assertEqual(absent.config_hash, empty_ctx.config_hash)

    def test_setting_inject_changes_hash(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "skill.md").write_text("BODY A", encoding="utf-8")
            r = StubResolver()
            without = resolve_scenario(load_scenario(self._write(tmp, "")), r)
            armed = resolve_scenario(
                load_scenario(self._write(tmp, '[context]\ninject = "skill.md"')), r
            )
            self.assertNotEqual(without.config_hash, armed.config_hash)

    def test_different_bodies_hash_differently(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "a.md").write_text("BODY A", encoding="utf-8")
            (tmp / "b.md").write_text("BODY B — different", encoding="utf-8")
            r = StubResolver()
            ra = resolve_scenario(load_scenario(self._write(tmp, '[context]\ninject = "a.md"')), r)
            rb = resolve_scenario(load_scenario(self._write(tmp, '[context]\ninject = "b.md"')), r)
            self.assertNotEqual(ra.config_hash, rb.config_hash)

    def test_inject_resolved_relative_to_scenario_dir(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "skill.md").write_text("BODY", encoding="utf-8")
            cfg = load_scenario(self._write(tmp, '[context]\ninject = "skill.md"'))
            self.assertTrue(os.path.isabs(cfg.context.inject))
            self.assertTrue(Path(cfg.context.inject).is_file())
```

Add `ContextConfig` to the imports at the top of the test file:
`from fathom.scenario import (..., ContextConfig, ...)`.

Run — watch it fail (no `ContextConfig`, no `context` field):
`uv run pytest tests/test_scenario.py -q` → **ImportError / AttributeError**.

**Step 1.2 — implement in `src/fathom/scenario.py`.**

(a) After `LimitsOverride` (around line 42), add:

```python
@dataclasses.dataclass(frozen=True)
class ContextConfig:
    """Per-scenario injected system-prompt context (a skill body / nudge).

    ``inject`` is an absolute path to a file whose body is appended to the spawn's
    default system prompt via ``--append-system-prompt-file`` (the treatment arm).
    ``None`` means no injection (the control arm). The treatment being measured is
    the file's *content*, so its sha256 — not the path — enters ``config_hash``:
    editing the body forks longitudinal history; relocating the file does not.
    """

    inject: str | None = None
```

(b) Add a `context` field (default) as the LAST field of both `ScenarioConfig` and
`ResolvedScenario`:

```python
    context: ContextConfig = dataclasses.field(default_factory=ContextConfig)
```

(c) In `load_scenario`, after parsing `limits`, resolve the inject path relative to the scenario
file's directory:

```python
    context_raw = data.get("context", {})
    inject = context_raw.get("inject")
    if inject is not None:
        inject_path = Path(inject)
        if not inject_path.is_absolute():
            inject_path = path.parent / inject_path
        inject = str(inject_path.resolve())
    context = ContextConfig(inject=inject)
```

and pass `context=context` to the `ScenarioConfig(...)` return.

(d) In `resolve_scenario`, compute the content hash and thread it through:

```python
    inject_sha: str | None = None
    if config.context.inject:
        try:
            inject_sha = hashlib.sha256(Path(config.context.inject).read_bytes()).hexdigest()
        except OSError:
            inject_sha = None  # missing/unreadable; the CLI factory warns (K7) at run time
```

Pass `inject_set=bool(config.context.inject)` and `inject_sha=inject_sha` into `_resolved_to_dict`,
and set `context=config.context` on the returned `ResolvedScenario`.

(e) Extend `_resolved_to_dict` signature with `inject_set: bool = False, inject_sha: str | None = None`
and include a context block **only when inject is set** (mirrors `_tools_to_dict`'s conditional):

```python
    d = {
        "adapter": adapter,
        ...
        "tools": _tools_to_dict(tools),
    }
    if inject_set:
        d["context"] = {"inject_sha": inject_sha}
    return d
```

Run to green: `uv run pytest tests/test_scenario.py -q` → **all pass**. Then
`uv run ruff format . && uv run ruff check . && uv run pytest -q` → **283+ pass**. Commit
`feat(scenario): context.inject field, content-hashed into config_hash`.

---

## T2 — adapter `--append-system-prompt-file`

**Files:** `src/fathom/adapters/claude_cli.py`, `tests/test_adapter_claude_cli.py`.
**Acceptance:** `build_command(append_system_prompt_file=p)` includes `--append-system-prompt-file p`;
omitted when `None`; a runner constructed with the path passes it through `execute`'s argv.

**Step 2.1 — failing tests.** Add to `tests/test_adapter_claude_cli.py`:

In `TestBuildCommand`:

```python
    def test_append_system_prompt_file_present_when_set(self):
        cmd = self._cmd(append_system_prompt_file="/abs/skill.md")
        self.assertIn("--append-system-prompt-file", cmd)
        self.assertEqual(cmd[cmd.index("--append-system-prompt-file") + 1], "/abs/skill.md")

    def test_append_system_prompt_file_absent_when_unset(self):
        self.assertNotIn("--append-system-prompt-file", self._cmd())
```

In `TestExecuteArgv`:

```python
    def test_inject_path_reaches_argv(self):
        spawn = RecordingSpawn(lambda i: _cp(0, _fixture("stream_complete.jsonl")))
        runner = self.make_runner(spawn, append_system_prompt_file="/abs/skill.md")
        runner.execute("p", self.workspace, _scenario())
        argv = spawn.calls[0].argv
        self.assertEqual(argv[argv.index("--append-system-prompt-file") + 1], "/abs/skill.md")
```

Run — watch fail (`build_command` has no such kwarg):
`uv run pytest tests/test_adapter_claude_cli.py -q` → **TypeError**.

**Step 2.2 — implement.** In `build_command` add the parameter and emit the flag (place after the
`--disallowed-tools` block, before the output-format block):

```python
def build_command(
    *,
    model: str,
    effort: str,
    max_turns: int,
    max_budget_usd: float,
    allowed_tools: Sequence[str],
    disallowed_tools: Sequence[str] = (),
    append_system_prompt_file: str | None = None,
    stream: bool = True,
) -> list[str]:
    ...
    if disallowed_tools:
        cmd += ["--disallowed-tools", ",".join(disallowed_tools)]
    if append_system_prompt_file:
        cmd += ["--append-system-prompt-file", append_system_prompt_file]
    if max_budget_usd:
        cmd += ["--max-budget-usd", str(max_budget_usd)]
    ...
```

In `ClaudeCliRunner.__init__`, add `append_system_prompt_file: str | None = None` and store it. In
`_run`, pass `append_system_prompt_file=self.append_system_prompt_file` to `build_command`.

Green: `uv run pytest tests/test_adapter_claude_cli.py -q`, then full gates. Commit
`feat(adapter): --append-system-prompt-file injection`.

---

## T3 — CLI factory wiring + smoke helper (K7)

**Files:** `src/fathom/cli.py`, `src/fathom/smoke.py`, `tests/test_cli.py`, `tests/test_smoke_logic.py`.
**Acceptance:** `_default_runner_factory` passes `scenario.context.inject` to the runner; a scenario
that declares `inject` pointing at a missing file prints a loud `WARNING` to stderr (the
unarmed-treatment guard); `injection_file_of` returns the flag's value or `None`.

**Step 3.1 — failing tests.** In `tests/test_cli.py` add (follow the file's existing import/style;
construct a `ResolvedScenario` via `fathom.scenario` with a `ContextConfig`):

```python
class TestRunnerFactoryInjection(unittest.TestCase):
    def _resolved(self, inject):
        from fathom.scenario import ContextConfig, LimitsOverride, ResolvedScenario, ToolsConfig

        return ResolvedScenario(
            name="pyeng-skill", adapter="claude-cli", model="m", strategy="single-session",
            effort="high", tools=ToolsConfig(source="none", allowed=("Read", "Write")),
            limits=LimitsOverride(), model_id=None, tool_repo_sha=None,
            tool_invocation_cmd=None, config_hash="x" * 64, context=ContextConfig(inject=inject),
        )

    def test_factory_passes_inject_to_runner(self):
        import tempfile
        from fathom.cli import _default_runner_factory

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("SKILL BODY")
            path = f.name
        runner = _default_runner_factory(self._resolved(path))
        self.assertEqual(runner.append_system_prompt_file, path)

    def test_factory_warns_on_missing_inject_file(self):
        import contextlib
        import io
        from fathom.cli import _default_runner_factory

        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            _default_runner_factory(self._resolved("/no/such/skill.md"))
        self.assertIn("UN-SKILLED", buf.getvalue())
```

In `tests/test_smoke_logic.py` add:

```python
def test_injection_file_of():
    from fathom.smoke import injection_file_of

    assert injection_file_of(["claude", "--append-system-prompt-file", "/a.md"]) == "/a.md"
    assert injection_file_of(["claude", "-p"]) is None
```

Run — watch fail.

**Step 3.2 — implement.** In `src/fathom/cli.py` `_default_runner_factory`:

```python
def _default_runner_factory(scenario: ResolvedScenario) -> Any:
    from fathom.adapters.claude_cli import ClaudeCliRunner

    inject = scenario.context.inject
    if scenario.strategy != "series" and not scenario.tools.allowed:
        print(
            f"WARNING: scenario '{scenario.name}' has an empty tools.allowed list; "
            "under default-deny the agent cannot read or write the workspace",
            file=sys.stderr,
        )
    if inject is not None and not pathlib.Path(inject).is_file():
        print(
            f"WARNING: scenario '{scenario.name}' declares context.inject but the file is "
            f"missing/unreadable ({inject}); the treatment arm would spawn UN-SKILLED",
            file=sys.stderr,
        )
    return ClaudeCliRunner(
        allowed_tools=scenario.tools.allowed,
        disallowed_tools=scenario.tools.disallowed,
        append_system_prompt_file=inject,
    )
```

In `src/fathom/smoke.py`, add near `permission_mode_of` (~line 185):

```python
def injection_file_of(argv: list[str]) -> str | None:
    """The --append-system-prompt-file value in *argv*, or None (K7 guard helper)."""
    if "--append-system-prompt-file" in argv:
        i = argv.index("--append-system-prompt-file")
        if i + 1 < len(argv):
            return argv[i + 1]
    return None
```

Green + gates. Commit `feat(cli): wire scenario.context.inject; warn on unarmed treatment`.

---

## T4 — report.py per-criterion table

**Files:** `src/fathom/report.py`, `tests/test_report.py`, `tests/fixtures/report/golden-scorecard.md`.
**Acceptance:** the scorecard gains a `### Per-Criterion Pass Rates` table (criterion rows ×
scenario columns, `% (passes/total)` over completed non-infra trials); the golden test passes after
regeneration.

**Step 4.1 — failing test.** Add to `tests/test_report.py`:

```python
def test_per_criterion_table_present_and_discriminates():
    content = _render_content()
    assert "### Per-Criterion Pass Rates" in content
    # criterion_1: bare passes on alpha, fails on beta → 1/2 = 50%
    crit_rows = [ln for ln in content.splitlines() if ln.startswith("| criterion_1 |")]
    assert crit_rows, "No criterion_1 row in per-criterion table"
    assert "50.0% (1/2)" in crit_rows[0], crit_rows[0]
```

Run — watch fail (no such section).

**Step 4.2 — implement.** In `src/fathom/report.py` `_section`, after the Verdicts block and before
the `if bare_ch:` pairwise block, insert:

```python
        # Per-criterion pass rates: separate compliance criteria from correctness
        # (the blended all-truthy pass-rate cannot show which criteria a scenario moved).
        crit_counts: dict[str, dict[str, list[int]]] = {}
        all_crits: set[str] = set()
        for sc in all_sc:
            for tid in task_list:
                for rep in reps_for.get((sc, tid), []):
                    t = trials.get((sc, tid, rep))
                    if t is None or t.get("infra_error") or t.get("status") != "completed":
                        continue
                    vr = t.get("verifier_results")
                    if not isinstance(vr, dict):
                        continue
                    for crit, val in vr.items():
                        all_crits.add(crit)
                        pc = crit_counts.setdefault(crit, {}).setdefault(sc, [0, 0])
                        pc[1] += 1
                        if val:
                            pc[0] += 1
        crit_scs = [sc for sc in all_sc if any(sc in crit_counts.get(c, {}) for c in all_crits)]
        if all_crits and crit_scs:
            lines.append("### Per-Criterion Pass Rates")
            lines.append("")
            lines.append("| Criterion | " + " | ".join(crit_scs) + " |")
            lines.append("|---|" + "|".join(["---"] * len(crit_scs)) + "|")
            for crit in sorted(all_crits):
                cells = []
                for sc in crit_scs:
                    pc = crit_counts.get(crit, {}).get(sc)
                    cells.append(f"{_pct(pc[0] / pc[1])} ({pc[0]}/{pc[1]})" if pc and pc[1] else "—")
                lines.append(f"| {crit} | " + " | ".join(cells) + " |")
            lines.append("")
```

Regenerate the golden: delete `tests/fixtures/report/golden-scorecard.md`, run
`uv run pytest tests/test_report.py::test_golden_scorecard -q` (it bootstraps), then **open the new
golden and confirm** it contains the per-criterion table with sane numbers. Run full
`uv run pytest tests/test_report.py -q`. Gates. Commit `feat(report): per-criterion pass-rate table`.

---

## T5 — skill-pyeng-v1 bank, fixture, verifier, scenarios

**Files:** under `tasks/skill-pyeng-v1/` and `scenarios/skill-pyeng/`, plus
`tests/test_bank_skill_pyeng_v1.py`.
**Acceptance:** `load_bank(Path("tasks/skill-pyeng-v1"))` loads one task; `verify.py` on the
untouched fixture reports all 5 compliance criteria `False` and `behavior_preserved True`; on a
minimally-modernized copy it reports the moved criteria `True`; the three scenario files parse and
resolve (control hash-stable, two treatments distinct); `fathom run skill-pyeng-v1 --scenarios-dir
scenarios/skill-pyeng --dry-run` prints `planned: 9 trials`.

**Step 5.1 — bank + fixture.** Create:

`tasks/skill-pyeng-v1/bank.toml`:
```toml
name = "skill-pyeng-v1"
dataset_version = "1"
holdout = []
```

`tasks/skill-pyeng-v1/modernize-timeflow/task.toml`:
```toml
id = "modernize-timeflow"
instruction = """
Modernize this Python project to production-quality standards. Improve its project
layout, packaging and tooling configuration, dependency management, and quality and
security tooling to current best practice. Preserve all existing behavior: the
existing tests must still pass and the public functions `parse_timestamp` and
`normalize` must keep their current behavior.
"""

[limits]
trial_timeout_s = 600
max_turns = 60

[verify]
entry = "verify.py"
```

`tasks/skill-pyeng-v1/modernize-timeflow/fixtures/timeflow/__init__.py`:
```python
"""timeflow — small timestamp helpers (legacy flat layout)."""
```

`tasks/skill-pyeng-v1/modernize-timeflow/fixtures/timeflow/parser.py`:
```python
"""Timestamp parsing and normalization."""

from datetime import datetime, timezone


def parse_timestamp(text):
    """Parse an ISO-8601 timestamp into a timezone-aware UTC datetime."""
    text = text.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize(text):
    """Normalize a timestamp string to canonical UTC ISO-8601 with a Z suffix."""
    return parse_timestamp(text).strftime("%Y-%m-%dT%H:%M:%SZ")
```

`tasks/skill-pyeng-v1/modernize-timeflow/fixtures/tests/__init__.py`: empty file.

`tasks/skill-pyeng-v1/modernize-timeflow/fixtures/tests/test_parser.py`:
```python
import unittest

from timeflow.parser import normalize, parse_timestamp


class TestParser(unittest.TestCase):
    def test_normalize_z(self):
        self.assertEqual(normalize("2026-06-13T12:00:00Z"), "2026-06-13T12:00:00Z")

    def test_normalize_offset(self):
        self.assertEqual(normalize("2026-06-13T14:00:00+02:00"), "2026-06-13T12:00:00Z")

    def test_parse_naive_assumes_utc(self):
        self.assertEqual(parse_timestamp("2026-06-13T12:00:00").hour, 12)


if __name__ == "__main__":
    unittest.main()
```

`tasks/skill-pyeng-v1/modernize-timeflow/fixtures/pyproject.toml` (legacy → doctor 0/5):
```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "timeflow"
version = "0.1.0"
description = "Timestamp helpers"
requires-python = ">=3.10"

[project.optional-dependencies]
dev = ["pytest", "black", "flake8"]
```

`tasks/skill-pyeng-v1/modernize-timeflow/fixtures/README.md`:
```markdown
# timeflow

Small timestamp helpers. Run tests with `python -m unittest discover -s tests -t .`.
```

**Step 5.2 — verifier.** `tasks/skill-pyeng-v1/modernize-timeflow/verify.py`:
```python
"""Acceptance verifier for modernize-timeflow (harness-side, scenario-blind, ADR-0003).

Reads ONLY the result-view path in argv[1]. The five compliance criteria are ported
verbatim from the python-engineering skill's own scripts/doctor.py audit (so the
treatment is graded against the skill's definition of its standard, not ours).
`behavior_preserved` imports the candidate timeflow.parser whether it ended up flat
or under src/ and checks the public functions still behave. Emits {criterion: bool}
JSON; exits 0 iff behavior_preserved (correctness gate). Compliance rides as criteria.
"""

import importlib.util
import json
import sys
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _compliance(d: Path) -> dict:
    pyproject = _read(d / "pyproject.toml")
    out: dict[str, bool] = {}
    src = d / "src"
    out["src-layout"] = src.is_dir() and any(c.is_dir() for c in src.iterdir())
    out["uv"] = (d / "uv.lock").is_file() or "uv_build" in pyproject or "[tool.uv]" in pyproject
    out["ruff-single-quote"] = (
        'quote-style = "single"' in pyproject or "quote-style = 'single'" in pyproject
    )
    out["dependency-groups"] = "[dependency-groups]" in pyproject
    ci_files = list(d.glob(".github/workflows/*.yml")) + list(d.glob(".github/workflows/*.yaml"))
    ci = " ".join(_read(p) for p in ci_files)
    out["pip-audit"] = "pip-audit" in pyproject or "pip-audit" in ci
    return out


def _find_parser(view: Path) -> Path | None:
    for base in (view / "timeflow", view / "src" / "timeflow"):
        cand = base / "parser.py"
        if cand.is_file():
            return cand
    for cand in view.rglob("timeflow/parser.py"):
        return cand
    return None


def _behavior_preserved(view: Path) -> bool:
    mod_path = _find_parser(view)
    if mod_path is None:
        return False
    try:
        spec = importlib.util.spec_from_file_location("tf_parser_under_test", mod_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return (
            mod.normalize("2026-06-13T12:00:00Z") == "2026-06-13T12:00:00Z"
            and mod.normalize("2026-06-13T14:00:00+02:00") == "2026-06-13T12:00:00Z"
        )
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = _compliance(view)
    results["behavior_preserved"] = _behavior_preserved(view)
    print(json.dumps(results, sort_keys=True))
    return 0 if results["behavior_preserved"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

**Step 5.3 — scenarios.** Create `scenarios/skill-pyeng/`:

`scenarios/skill-pyeng/bare.toml` (control — copy of the repo `bare.toml`):
```toml
name = "bare"
adapter = "claude-cli"
model = "claude-opus-4-8"
strategy = "single-session"
effort = "high"

[tools]
source = "none"
allowed = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)"]

[limits]
trial_timeout_s = 600
```

`scenarios/skill-pyeng/generic-nudge.toml` (= bare + inject):
```toml
name = "generic-nudge"
adapter = "claude-cli"
model = "claude-opus-4-8"
strategy = "single-session"
effort = "high"

[tools]
source = "none"
allowed = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)"]

[context]
inject = "assets/generic-nudge.md"

[limits]
trial_timeout_s = 600
```

`scenarios/skill-pyeng/pyeng-skill.toml` (= bare + inject):
```toml
name = "pyeng-skill"
adapter = "claude-cli"
model = "claude-opus-4-8"
strategy = "single-session"
effort = "high"

[tools]
source = "none"
allowed = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)"]

[context]
inject = "assets/python-engineering.md"

[limits]
trial_timeout_s = 600
```

`scenarios/skill-pyeng/assets/generic-nudge.md`:
```markdown
Write production-quality, well-structured, idiomatic Python. Use a clean project
layout, configure standard tooling (formatter, linter, type checker, tests), manage
dependencies properly, and include basic quality and security checks.
```

`scenarios/skill-pyeng/assets/python-engineering.md` — **vendor the skill body verbatim**. Exact
command (the pinned treatment asset, committed so the experiment is reproducible):
```
Copy C:\Users\grima\.claude\plugins\cache\craft-collection\engineering-discipline\0.1.2\skills\python-engineering\SKILL.md
  to scenarios\skill-pyeng\assets\python-engineering.md
```
(Use `Read` then `Write`, or `Copy-Item`. Do not edit the body — it is the treatment.)

**Step 5.4 — bank test.** `tests/test_bank_skill_pyeng_v1.py`:
```python
"""Tests for the skill-pyeng-v1 bank and its verifier — stdlib-runnable."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.taskbank import load_bank

BANK_DIR = Path(__file__).parent.parent / "tasks" / "skill-pyeng-v1"
TASK_DIR = BANK_DIR / "modernize-timeflow"


class TestBank(unittest.TestCase):
    def test_bank_loads_one_task(self):
        bank = load_bank(BANK_DIR)
        self.assertEqual(bank.name, "skill-pyeng-v1")
        self.assertEqual(bank.dataset_version, "1")
        self.assertEqual([t.id for t in bank.tasks], ["modernize-timeflow"])
        self.assertEqual(bank.holdout, [])


def _run_verifier(view: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(TASK_DIR / "verify.py"), str(view)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(proc.stdout)


class TestVerifier(unittest.TestCase):
    def test_untouched_fixture_is_noncompliant_but_correct(self):
        view = TASK_DIR / "fixtures"
        results = _run_verifier(view)
        self.assertTrue(results["behavior_preserved"])
        for crit in ("src-layout", "uv", "ruff-single-quote", "dependency-groups", "pip-audit"):
            self.assertFalse(results[crit], f"{crit} should be False on the legacy fixture")

    def test_modernized_copy_flips_compliance(self):
        with tempfile.TemporaryDirectory() as td:
            view = Path(td)
            pkg = view / "src" / "timeflow"
            pkg.mkdir(parents=True)
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "parser.py").write_text(
                (TASK_DIR / "fixtures" / "timeflow" / "parser.py").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (view / "uv.lock").write_text("", encoding="utf-8")
            (view / "pyproject.toml").write_text(
                '[tool.ruff.format]\nquote-style = "single"\n\n[dependency-groups]\n'
                'dev = ["pytest", "pip-audit"]\n',
                encoding="utf-8",
            )
            results = _run_verifier(view)
            self.assertTrue(results["behavior_preserved"])
            self.assertTrue(results["src-layout"])
            self.assertTrue(results["uv"])
            self.assertTrue(results["ruff-single-quote"])
            self.assertTrue(results["dependency-groups"])
            self.assertTrue(results["pip-audit"])


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
```

**Step 5.5 — verify wiring.** Run:
- `uv run pytest tests/test_bank_skill_pyeng_v1.py -q` → pass.
- `uv run pytest -q` → all pass.
- Gates: `uv run ruff format --check . && uv run ruff check .`.
- Dry-run plan: `uv run fathom run skill-pyeng-v1 --scenarios-dir scenarios/skill-pyeng --dry-run`
  → prints `scenarios=3  tasks=1  repeats=2` and `planned: 6 trials` (default repeats=2; the real
  run will pass `--repeats 3` for 9). Confirm no warnings about unarmed treatment (the asset files
  exist).

Commit `feat(bank): skill-pyeng-v1 modernize-timeflow + skill-pyeng scenarios`.

---

## Post-execution

1. Final whole-plan review subagent: every File-map row delivered, every acceptance criterion met,
   no placeholder survived.
2. Hand the "done" to verification-before-completion: run the three gate commands fresh +
   the dry-run plan, paste output.
3. **The paid run is a separate, user-gated step** (≈$5–18): `uv run fathom smoke` then
   `uv run fathom run skill-pyeng-v1 --scenarios-dir scenarios/skill-pyeng --repeats 3`, then
   `uv run fathom report skill-pyeng-v1`. Do not spend money without explicit go-ahead.

## Self-review (controller, pre-execution)

- Every File-map file maps to a task; every spec §4 concept covered (inject → T1, adapter → T2,
  cli warn → T3, smoke helper → T3, report table → T4, verifier/fixture/scenarios/bank → T5). ✓
- Signatures consistent across tasks: `ContextConfig.inject` (T1) → `ResolvedScenario.context`
  (T1) → factory reads `scenario.context.inject` (T3) → `ClaudeCliRunner(append_system_prompt_file=)`
  (T2) → `build_command(append_system_prompt_file=)` (T2). ✓
- No placeholders; all code complete; the one "copy" step (vendoring SKILL.md) names an exact
  source path, not a TBD. ✓
- Scenarios isolated in `scenarios/skill-pyeng/` so the series-engine matrix is untouched; the committed
  series-engine bank's ledger hashes are preserved by the absent==no-context hash rule (T1 acceptance). ✓
