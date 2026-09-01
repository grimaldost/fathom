# PR02 — Comparison operators

You are working in the `exprlang` package: a small expression language, pure standard
library, no new dependencies. Layout:

- `exprlang/lexer.py` — tokenizer (source string -> list of `Token`, ending in `EOF`)
- `exprlang/parser.py` — Pratt parser -> nested-tuple AST (`("num", v)`, `("bool", v)`,
  `("var", n)`, `("unary", op, operand)`, `("binary", op, left, right)`)
- `exprlang/evaluator.py` — AST evaluator; public entry point `exprlang.evaluate(expr, env=None)`
- `exprlang/errors.py` — error hierarchy rooted at `ExprError`

**This is PR02 of 5.** PR01 already landed: values are `int`, `float` and `bool`, the
literals `true` / `false` parse to a `("bool", v)` AST node, `TypeMismatchError` exists as
a subclass of `ExprError`, the arithmetic operators reject boolean operands, and the
evaluator carries a numeric-operand guard and a boolean-operand guard. Read that code
before you start and reuse the guards — do not write a second copy of either.

## What this PR delivers

The six comparison operators: `==`, `!=`, `<`, `<=`, `>`, `>=`.

1. **Lexing.** They are new tokens.

2. **Parsing.** They are binary and left-associative. In the language's precedence table,
   from LOWEST to HIGHEST binding:

   ```
   or  <  and  <  not  <  (comparisons)  <  + -  <  * / %  <  unary - +
   ```

   So comparisons bind LOOSER than the arithmetic operators: an arithmetic expression on
   either side of a comparison groups tighter than the comparison itself. The `or` / `and`
   / `not` levels are PR03 and PR04's work; this PR only has to put the comparison level
   in the right place relative to arithmetic.

3. **Evaluation.** A comparison requires TWO NUMERIC (int or float) operands and produces
   a `bool`. An operand of the wrong type raises `TypeMismatchError` — use PR01's numeric
   guard rather than a fresh check.

## Interface this PR must publish (later PRs depend on it)

- The comparison level in the parser's precedence table, so PR03 can add `and` / `or`
  BELOW it and PR04 can add `not` between them.
- Comparison results are ordinary booleans, so PR03's `and` / `or` accept them without a
  special case.

## Out of scope for this PR

`and`, `or`, `not` (PR03 and PR04). Do not add them.

## Constraints

- Standard library only; add no dependencies.
- **Do not modify or delete `tests/test_arithmetic.py` or `tests/test_feature.py`.**
  `tests/test_arithmetic.py` is the baseline and must stay green; `tests/test_feature.py`
  describes the whole five-PR feature, so parts of it are still red after this PR — that is
  expected, and it is not yours to edit.
- The tests an EARLIER PR of this series added under `tests/` are yours to correct: if one
  of them contradicts the specification in this brief, fix that test. The two files named
  above are the only ones that are fixed.
- Add your own tests for what this PR delivers in a NEW file under `tests/`.

## How this PR is judged

Three blocking checks run from the project root:

```
python -m unittest discover -s tests -t . -p "test_arithmetic.py"
python -m unittest tests.test_feature.TestFeature.test_bool_literals
python -m unittest tests.test_feature.TestFeature.test_comparisons tests.test_feature.TestFeature.test_precedence_compare_below_arithmetic
```
