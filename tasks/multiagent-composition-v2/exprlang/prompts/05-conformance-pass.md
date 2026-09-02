# PR05 — Conformance pass: the precedence table, end to end

You are working in the `exprlang` package: a small expression language, pure standard
library, no new dependencies. Layout:

- `exprlang/lexer.py` — tokenizer (source string -> list of `Token`, ending in `EOF`)
- `exprlang/parser.py` — Pratt parser -> nested-tuple AST (`("num", v)`, `("bool", v)`,
  `("var", n)`, `("unary", op, operand)`, `("binary", op, left, right)`)
- `exprlang/evaluator.py` — AST evaluator; public entry point `exprlang.evaluate(expr, env=None)`
- `exprlang/errors.py` — error hierarchy rooted at `ExprError`

**This is PR05 of 5, the last one.** PR01–PR04 landed the feature one level at a time:
boolean literals, the six comparison operators, `and` / `or` with short-circuiting, and
`not`. Each of those PRs could only see its own level of the language. One requirement
spans all of them and therefore belongs to no single earlier PR; this PR owns it, plus
the feature's testing requirement.

## 1. The precedence table, as a whole

From LOWEST to HIGHEST binding:

```
or  <  and  <  not  <  (comparisons)  <  + -  <  * / %  <  unary - +
```

All binary operators are left-associative; `not` and unary `-` / `+` are prefix. Four PRs
each inserted one level into this table without being able to check the neighbours they
did not add. Verify the ordering holds, and fix the parser where it does not.

## 2. The tests the feature owes

The feature's testing requirement is: unit tests under `tests/` covering the new behaviour
— comparisons, `and` / `or` / `not`, short-circuiting in BOTH directions, the precedence
rules, and the type errors. PR01–PR04 each added tests for their own level. Close whatever
that leaves uncovered, in a NEW file under `tests/`.

## Also required

Everything the language did before this series must still work: the existing arithmetic
semantics, the error types `LexError` / `ParseError` / `EvalError`, and the
division/modulo-by-zero handling must not have regressed.

## Constraints

- Standard library only; add no dependencies.
- **Do not modify or delete `tests/test_arithmetic.py` or `tests/test_feature.py`.** If a
  test in either of those two files fails, the implementation is what changes.
- The tests PR01–PR04 of this series added under `tests/` are yours to correct: each was
  written against one level of the language in isolation, so if one of them contradicts
  the specification above or the finished feature, fix that test. The two files named
  above are the only ones that are fixed.

## How this PR is judged

Two blocking checks run from the project root — the baseline suite, and the project's
whole visible suite:

```
python -m unittest discover -s tests -t . -p "test_arithmetic.py"
python -m unittest discover -s tests -t .
```
