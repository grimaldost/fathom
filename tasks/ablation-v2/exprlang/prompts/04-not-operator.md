# PR04 — The `not` operator and its place in the precedence table

You are working in the `exprlang` package: a small expression language, pure standard
library, no new dependencies. Layout:

- `exprlang/lexer.py` — tokenizer (source string -> list of `Token`, ending in `EOF`)
- `exprlang/parser.py` — Pratt parser -> nested-tuple AST (`("num", v)`, `("bool", v)`,
  `("var", n)`, `("unary", op, operand)`, `("binary", op, left, right)`)
- `exprlang/evaluator.py` — AST evaluator; public entry point `exprlang.evaluate(expr, env=None)`
- `exprlang/errors.py` — error hierarchy rooted at `ExprError`

**This is PR04 of 5.** PR01–PR03 already landed: `true` / `false` are literals,
`TypeMismatchError` exists as a subclass of `ExprError`, the evaluator carries a
numeric-operand guard and a boolean-operand guard, arithmetic rejects booleans, the six
comparison operators work on numeric operands and produce booleans, and `and` / `or` work
on boolean operands with short-circuiting. Read that code before you start and reuse the
guards — do not write a second copy of either.

## What this PR delivers

The prefix operator `not`.

1. **Lexing.** A keyword, like `and` and `or`.

2. **Parsing.** `not` is a PREFIX operator, and its position in the precedence table is
   the whole point of this PR. From LOWEST to HIGHEST binding:

   ```
   or  <  and  <  not  <  (comparisons)  <  + -  <  * / %  <  unary - +
   ```

   `not` binds TIGHTER than `and` and `or`, and LOOSER than the comparison operators, so
   `not 1 < 2` parses as `not (1 < 2)`.

3. **Evaluation.** `not` requires a BOOLEAN operand and produces a `bool`; an operand of
   the wrong type raises `TypeMismatchError`. Use PR01's boolean guard.

## Out of scope for this PR

Nothing new is added after this PR. PR05 is a conformance pass over the finished feature.

## Constraints

- Standard library only; add no dependencies.
- **Do not modify or delete `tests/test_arithmetic.py` or `tests/test_feature.py`.**
  `tests/test_arithmetic.py` is the baseline and must stay green.
- The tests an EARLIER PR of this series added under `tests/` are yours to correct: if one
  of them contradicts the specification in this brief, fix that test. The two files named
  above are the only ones that are fixed.
- Add your own tests for what this PR delivers in a NEW file under `tests/`, including
  the parse-shape case above.

## How this PR is judged

Five blocking checks run from the project root:

```
python -m unittest discover -s tests -t . -p "test_arithmetic.py"
python -m unittest tests.test_feature.TestFeature.test_bool_literals
python -m unittest tests.test_feature.TestFeature.test_comparisons tests.test_feature.TestFeature.test_precedence_compare_below_arithmetic
python -m unittest tests.test_feature.TestFeature.test_and_or_values tests.test_feature.TestFeature.test_and_short_circuits tests.test_feature.TestFeature.test_type_error_number_in_boolean_op tests.test_feature.TestFeature.test_precedence_bool_below_compare
python -m unittest tests.test_feature.TestFeature.test_not
```
