# exprlang (starting fixture)

A tiny expression-language package. Today it evaluates integer/float arithmetic
with correct precedence, unary minus, parentheses, variables, and
division/modulo-by-zero errors. The code is split across:

- `exprlang/lexer.py` -- tokenizer
- `exprlang/parser.py` -- Pratt parser -> tuple AST
- `exprlang/evaluator.py` -- AST evaluator (public `evaluate`)
- `exprlang/errors.py` -- error hierarchy

Run the tests from this directory:

    python -m unittest discover -s tests -t .

`tests/test_arithmetic.py` is the baseline (green now, keep it green).
`tests/test_feature.py` describes the comparison/boolean feature to add (red now).
