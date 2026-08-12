# numerals

`to_roman(n)` renders 1..3999 in standard Roman numerals, using the
subtractive forms IV, IX, XL, XC, CD and CM rather than four repeats.

`BASE_VALUES` is the canonical single-symbol ladder and other modules import
it, so it must keep exactly its seven entries. The subtractive forms are
derived inside `to_roman`, never added to `BASE_VALUES`.
