# PR03 — `and` and `or`, with short-circuiting

You are working in the `exprlang` package: a small expression language, pure standard
library, no new dependencies. Layout:

- `exprlang/lexer.py` — tokenizer (source string -> list of `Token`, ending in `EOF`)
- `exprlang/parser.py` — Pratt parser -> nested-tuple AST (`("num", v)`, `("bool", v)`,
  `("var", n)`, `("unary", op, operand)`, `("binary", op, left, right)`)
- `exprlang/evaluator.py` — AST evaluator; public entry point `exprlang.evaluate(expr, env=None)`
- `exprlang/errors.py` — error hierarchy rooted at `ExprError`

**This is PR03 of 5.** PR01 and PR02 already landed: `true` / `false` are literals,
`TypeMismatchError` exists as a subclass of `ExprError`, the evaluator carries a
numeric-operand guard and a boolean-operand guard, arithmetic rejects booleans, and the
six comparison operators (`== != < <= > >=`) take two numeric operands, reject operands of
the wrong type, and produce a `bool`. Read that code before you start and reuse the guards
— do not write a second copy of either.

## What this PR delivers

The binary boolean operators `and` and `or`.

1. **Lexing.** They are keywords, like `true` and `false` — not variables.

2. **Parsing.** Both are binary and left-associative. In the language's precedence table,
   from LOWEST to HIGHEST binding:

   ```
   or  <  and  <  not  <  (comparisons)  <  + -  <  * / %  <  unary - +
   ```

   `or` binds loosest of all; `and` binds tighter than `or` and looser than everything to
   its right, so `1 < 2 and 3 < 4` parses as `(1 < 2) and (3 < 4)`. `not` is PR04's work;
   leave a place for it between `and` and the comparisons.

3. **Evaluation.** Both require BOOLEAN operands and produce a `bool`; an operand of the
   wrong type raises `TypeMismatchError`. Use PR01's boolean guard.

4. **Short-circuiting.** `and` evaluates its right operand only if the left is `True`;
   `or` evaluates its right operand only if the left is `False`. Because of
   short-circuiting, the right operand's errors are suppressed when the left already
   decides the result — `false and (1 / 0 > 0)` evaluates to `False` and MUST NOT raise,
   while `true and (1 / 0 > 0)` DOES raise. The same rule applies to `or`, in the
   direction its own short-circuit takes.

   Both operands are therefore not always evaluated, which is not true of any operator the
   evaluator handles today.

## Interface this PR must publish (later PRs depend on it)

- The `or` and `and` levels in the parser's precedence table, with room between `and` and
  the comparison level for PR04's `not`.

## Out of scope for this PR

`not` (PR04). Do not add it.

## Constraints

- Standard library only; add no dependencies.
- **Do not modify or delete any existing test.** `tests/test_arithmetic.py` is the
  baseline and must stay green; `tests/test_feature.py` describes the whole five-PR
  feature, so part of it is still red after this PR — that is expected, and it is not
  yours to edit.
- Add your own tests for what this PR delivers in a NEW file under `tests/`, covering
  short-circuiting in BOTH directions and both the suppressed and the propagated case.

## How this PR is judged

Four blocking checks run from the project root:

```
python -m unittest discover -s tests -t . -p "test_arithmetic.py"
python -m unittest tests.test_feature.TestFeature.test_bool_literals
python -m unittest tests.test_feature.TestFeature.test_comparisons tests.test_feature.TestFeature.test_precedence_compare_below_arithmetic
python -m unittest tests.test_feature.TestFeature.test_and_or_values tests.test_feature.TestFeature.test_and_short_circuits tests.test_feature.TestFeature.test_type_error_number_in_boolean_op tests.test_feature.TestFeature.test_precedence_bool_below_compare
```
