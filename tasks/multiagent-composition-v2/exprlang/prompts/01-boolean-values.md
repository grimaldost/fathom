# PR01 — Boolean values

You are working in the `exprlang` package: a small expression language, pure standard
library, no new dependencies. Layout:

- `exprlang/lexer.py` — tokenizer (source string -> list of `Token`, ending in `EOF`)
- `exprlang/parser.py` — Pratt parser -> nested-tuple AST (`("num", v)`, `("var", n)`,
  `("unary", op, operand)`, `("binary", op, left, right)`)
- `exprlang/evaluator.py` — AST evaluator; public entry point `exprlang.evaluate(expr, env=None)`
- `exprlang/errors.py` — error hierarchy rooted at `ExprError`

Today the language evaluates `int` / `float` arithmetic: `+ - * / %`, unary `-` / `+`,
parentheses, variables, and division/modulo-by-zero errors. This series adds comparison
and boolean operators across five PRs. **This is PR01 of 5.**

## What this PR delivers

Values become `int`, `float`, and now `bool`. This PR introduces the boolean value.

1. **A new error type.** Add `TypeMismatchError` to `exprlang/errors.py` as a NEW subclass
   of the existing `ExprError`, and export it from the `exprlang` package alongside the
   existing error names. Every later PR in this series raises it, so it lands here.

2. **Boolean literals.** `true` and `false` evaluate to Python `True` / `False`. They are
   keywords, not variables.

3. **Existing arithmetic is unchanged.** Existing arithmetic on numbers keeps working
   exactly as it does today — that behaviour is under test and must not regress.

## Interface this PR must publish (later PRs depend on it)

- **AST node for a boolean literal:** `("bool", True)` / `("bool", False)`. PR02–PR04 add
  operators that produce and consume booleans and will read this tag.
- **`TypeMismatchError`**, importable from both `exprlang.errors` and `exprlang`.

## Out of scope for this PR

Comparison operators (`== != < <= > >=`), the boolean operators (`and`, `or`, `not`), and
their precedence. Do not start them; later PRs own them and will build on the interface
above.

## Constraints

- Standard library only; add no dependencies.
- **Do not modify or delete `tests/test_arithmetic.py` or `tests/test_feature.py`.**
  `tests/test_arithmetic.py` is the baseline and must stay green; `tests/test_feature.py`
  describes the whole five-PR feature, so most of it is still red after this PR — that is
  expected, and it is not yours to edit.
- Add your own tests for what this PR delivers in a NEW file under `tests/`. A later PR of
  this series may correct one of them if it turns out to contradict that PR's brief.

## How this PR is judged

Two blocking checks run from the project root:

```
python -m unittest discover -s tests -t . -p "test_arithmetic.py"
python -m unittest tests.test_feature.TestFeature.test_bool_literals
```
