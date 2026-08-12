"""BUG class: a single-function defect with a stashed original and a shipped suite
that is green on the buggy code by construction.

Every domain is invented and public-safe.  The shipped baseline cases exercise only
the paths the bug does not touch, so a red after the inverse edit can only come from
a check the candidate added.  ``generate.py`` mechanically proves that property for
every task: base cases must pass on the buggy source, edge cases must fail on it and
pass on the fixed source.  An authoring slip therefore fails the generator rather
than the run.
"""

from __future__ import annotations

BUG = [
    dict(
        id="bug-even-split",
        package="allocate",
        module="split",
        func="split_amount",
        contract=(
            "`split_amount(total, parts)` divides a whole `total` into `parts` integer\n"
            "shares that are as equal as possible and add back up to `total` exactly.\n"
            "Leftover units go to the earliest shares, so the shares come out\n"
            "non-increasing."
        ),
        buggy='''def split_amount(total: int, parts: int) -> list[int]:
    """Divide *total* into *parts* near-equal integer shares."""
    base = total // parts
    return [base] * parts
''',
        fixed='''def split_amount(total: int, parts: int) -> list[int]:
    """Divide *total* into *parts* near-equal integer shares."""
    base, remainder = divmod(total, parts)
    return [base + (1 if i < remainder else 0) for i in range(parts)]
''',
        base_cases=[[[90, 3], [30, 30, 30]], [[8, 4], [2, 2, 2, 2]]],
        edge_cases=[[[100, 3], [34, 33, 33]], [[7, 2], [4, 3]]],
        instruction=(
            "`allocate.split.split_amount` drops the leftover units when `total` does not\n"
            "divide evenly by `parts`, so the shares add up to less than `total`. Hand the\n"
            "remainder out the way the package README describes, leaving the evenly\n"
            "divisible cases as they are and keeping the public API unchanged."
        ),
    ),
    dict(
        id="bug-page-window",
        package="paging",
        module="window",
        func="page_bounds",
        contract=(
            "`page_bounds(total, per_page)` returns the `(start, end)` half-open index\n"
            "pair of every page needed to cover `total` items, including a final partial\n"
            "page. `end` never exceeds `total`."
        ),
        buggy='''def page_bounds(total: int, per_page: int) -> list[list[int]]:
    """Half-open (start, end) bounds for each page covering *total* items."""
    pages = total // per_page
    return [[i * per_page, (i + 1) * per_page] for i in range(pages)]
''',
        fixed='''def page_bounds(total: int, per_page: int) -> list[list[int]]:
    """Half-open (start, end) bounds for each page covering *total* items."""
    bounds = []
    start = 0
    while start < total:
        bounds.append([start, min(start + per_page, total)])
        start += per_page
    return bounds
''',
        base_cases=[[[20, 5], [[0, 5], [5, 10], [10, 15], [15, 20]]], [[6, 3], [[0, 3], [3, 6]]]],
        edge_cases=[
            [[22, 5], [[0, 5], [5, 10], [10, 15], [15, 20], [20, 22]]],
            [[4, 10], [[0, 4]]],
        ],
        instruction=(
            "`paging.window.page_bounds` loses the final partial page: when `total` is not a\n"
            "multiple of `per_page` the trailing items are never covered by any returned\n"
            "range. Cover every item exactly once per the README contract, without changing\n"
            "the shape of the return value."
        ),
    ),
    dict(
        id="bug-roman-numeral",
        package="numerals",
        module="roman",
        func="to_roman",
        contract=(
            "`to_roman(n)` renders 1..3999 in standard Roman numerals, using the\n"
            "subtractive forms IV, IX, XL, XC, CD and CM rather than four repeats.\n\n"
            "`BASE_VALUES` is the canonical single-symbol ladder and other modules import\n"
            "it, so it must keep exactly its seven entries. The subtractive forms are\n"
            "derived inside `to_roman`, never added to `BASE_VALUES`."
        ),
        buggy='''BASE_VALUES = [
    (1000, "M"),
    (500, "D"),
    (100, "C"),
    (50, "L"),
    (10, "X"),
    (5, "V"),
    (1, "I"),
]


def to_roman(n: int) -> str:
    """Render *n* as a Roman numeral."""
    ladder = list(BASE_VALUES)
    out = []
    for value, symbol in ladder:
        while n >= value:
            out.append(symbol)
            n -= value
    return "".join(out)
''',
        fixed='''BASE_VALUES = [
    (1000, "M"),
    (500, "D"),
    (100, "C"),
    (50, "L"),
    (10, "X"),
    (5, "V"),
    (1, "I"),
]


def to_roman(n: int) -> str:
    """Render *n* as a Roman numeral."""
    ladder = []
    for index, (value, symbol) in enumerate(BASE_VALUES):
        ladder.append((value, symbol))
        for smaller, small_symbol in BASE_VALUES[index + 1 :]:
            if value - smaller in (900, 400, 90, 40, 9, 4):
                ladder.append((value - smaller, small_symbol + symbol))
                break
    ladder.sort(reverse=True)
    out = []
    for value, symbol in ladder:
        while n >= value:
            out.append(symbol)
            n -= value
    return "".join(out)
''',
        base_cases=[[[3], "III"], [[2026], "MMXXVI"], [[15], "XV"]],
        edge_cases=[[[4], "IV"], [[9], "IX"], [[1944], "MCMXLIV"]],
        instruction=(
            "`numerals.roman.to_roman` writes four repeats where the standard subtractive\n"
            "form belongs, so 4 comes out as IIII and 900 as DCCCC. Produce the standard\n"
            "forms the README lists, for every value in the supported range. As the README\n"
            "says, `BASE_VALUES` is shared with other modules and keeps its seven entries;\n"
            "derive the subtractive forms inside `to_roman`."
        ),
    ),
    dict(
        id="bug-word-wrap",
        package="textkit",
        module="wrap",
        func="wrap_words",
        contract=(
            "`wrap_words(text, width)` splits `text` on whitespace and packs words into\n"
            "lines no longer than `width`. A single word longer than `width` gets a line\n"
            "of its own rather than being dropped."
        ),
        buggy='''def wrap_words(text: str, width: int) -> list[str]:
    """Pack the words of *text* into lines of at most *width* characters."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        if len(word) > width:
            continue
        candidate = word if not current else current + " " + word
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
''',
        fixed='''def wrap_words(text: str, width: int) -> list[str]:
    """Pack the words of *text* into lines of at most *width* characters."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        if len(word) > width:
            if current:
                lines.append(current)
                current = ""
            lines.append(word)
            continue
        candidate = word if not current else current + " " + word
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
''',
        base_cases=[
            [["one two three", 9], ["one two", "three"]],
            [["a b c", 5], ["a b c"]],
        ],
        edge_cases=[
            [["ok unbreakablewordhere ok", 6], ["ok", "unbreakablewordhere", "ok"]],
            [["supercalifragilistic", 5], ["supercalifragilistic"]],
        ],
        instruction=(
            "`textkit.wrap.wrap_words` silently discards any word longer than `width`, so\n"
            "text goes missing from the wrapped output. Give an over-long word its own line\n"
            "as the README describes; leave the packing of ordinary words alone."
        ),
    ),
    dict(
        id="bug-run-length",
        package="rlekit",
        module="encode",
        func="encode_runs",
        contract=(
            "`encode_runs(text)` returns `[[char, count], ...]` for each consecutive run\n"
            "in `text`, including the final run. An empty input returns an empty list."
        ),
        buggy='''def encode_runs(text: str) -> list[list]:
    """Run-length encode *text* as [char, count] pairs."""
    runs: list[list] = []
    previous = ""
    count = 0
    for char in text:
        if char == previous:
            count += 1
        else:
            if previous:
                runs.append([previous, count])
            previous = char
            count = 1
    return runs
''',
        fixed='''def encode_runs(text: str) -> list[list]:
    """Run-length encode *text* as [char, count] pairs."""
    runs: list[list] = []
    previous = ""
    count = 0
    for char in text:
        if char == previous:
            count += 1
        else:
            if previous:
                runs.append([previous, count])
            previous = char
            count = 1
    if previous:
        runs.append([previous, count])
    return runs
''',
        base_cases=[[[""], []]],
        edge_cases=[[["aaabb"], [["a", 3], ["b", 2]]], [["x"], [["x", 1]]]],
        instruction=(
            "`rlekit.encode.encode_runs` never flushes the run it is accumulating when the\n"
            "input ends, so the last run is missing from the result. Emit every run per the\n"
            "README, leaving the empty-input behaviour as it is."
        ),
    ),
    dict(
        id="bug-interval-merge",
        package="intervals",
        module="merge",
        func="merge_spans",
        contract=(
            "`merge_spans(spans)` merges overlapping AND touching half-open spans and\n"
            "returns them sorted. `[0, 5]` and `[5, 9]` touch and merge to `[0, 9]`."
        ),
        buggy='''def merge_spans(spans: list[list[int]]) -> list[list[int]]:
    """Merge overlapping or touching half-open spans."""
    merged: list[list[int]] = []
    for start, end in sorted(spans):
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
''',
        fixed='''def merge_spans(spans: list[list[int]]) -> list[list[int]]:
    """Merge overlapping or touching half-open spans."""
    merged: list[list[int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
''',
        base_cases=[
            [[[[0, 4], [2, 7]]], [[0, 7]]],
            [[[[0, 2], [5, 8]]], [[0, 2], [5, 8]]],
        ],
        edge_cases=[
            [[[[0, 5], [5, 9]]], [[0, 9]]],
            [[[[1, 3], [3, 4], [4, 6]]], [[1, 6]]],
        ],
        instruction=(
            "`intervals.merge.merge_spans` treats two spans that merely touch as separate,\n"
            "so `[0, 5]` and `[5, 9]` come back as two spans instead of one. Merge touching\n"
            "spans as the README requires; overlapping spans already behave."
        ),
    ),
    dict(
        id="bug-base-convert",
        package="numerals",
        module="base",
        func="to_base",
        contract=(
            "`to_base(n, base)` renders a non-negative `n` in `base` 2..16 using the\n"
            'digits 0-9a-f. Zero renders as the single digit `"0"`.'
        ),
        buggy='''DIGITS = "0123456789abcdef"


def to_base(n: int, base: int) -> str:
    """Render non-negative *n* in *base* using 0-9a-f."""
    out = ""
    while n > 0:
        n, rem = divmod(n, base)
        out = DIGITS[rem] + out
    return out
''',
        fixed='''DIGITS = "0123456789abcdef"


def to_base(n: int, base: int) -> str:
    """Render non-negative *n* in *base* using 0-9a-f."""
    if n == 0:
        return "0"
    out = ""
    while n > 0:
        n, rem = divmod(n, base)
        out = DIGITS[rem] + out
    return out
''',
        base_cases=[[[10, 2], "1010"], [[255, 16], "ff"], [[7, 8], "7"]],
        edge_cases=[[[0, 2], "0"], [[0, 16], "0"]],
        instruction=(
            "`numerals.base.to_base` returns the empty string for zero instead of the\n"
            "single digit the README specifies. Render zero correctly in every supported\n"
            "base without disturbing the non-zero cases."
        ),
    ),
    dict(
        id="bug-checksum-mod",
        package="validate2",
        module="luhn",
        func="is_valid",
        contract=(
            "`is_valid(digits)` applies the mod-10 double-every-second-digit-from-the-right\n"
            "rule. The doubling anchors at the RIGHT end, so it works for odd and even\n"
            "lengths alike."
        ),
        buggy='''def is_valid(digits: str) -> bool:
    """Mod-10 checksum: double every second digit counting from the right."""
    total = 0
    for index, char in enumerate(digits):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0
''',
        fixed='''def is_valid(digits: str) -> bool:
    """Mod-10 checksum: double every second digit counting from the right."""
    total = 0
    for offset, char in enumerate(reversed(digits)):
        value = int(char)
        if offset % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0
''',
        base_cases=[[["22"], False], [["1111"], False], [["79927398710"], False]],
        edge_cases=[[["18"], True], [["1230"], True], [["4539578763621486"], True]],
        instruction=(
            "`validate2.luhn.is_valid` anchors the doubling at the left end of the string,\n"
            "so odd-length inputs double the wrong digits and valid numbers are rejected.\n"
            "Anchor at the right end as the README states; keep the signature."
        ),
    ),
    dict(
        id="bug-time-window",
        package="sched",
        module="window",
        func="slots",
        contract=(
            "`slots(start, end, step)` lists the slot start minutes in `[start, end)`.\n"
            "A slot that begins exactly at `end - step` is included; one that would begin\n"
            "at `end` is not."
        ),
        buggy='''def slots(start: int, end: int, step: int) -> list[int]:
    """Slot start minutes covering the half-open window [start, end)."""
    out = []
    current = start
    while current + step < end:
        out.append(current)
        current += step
    return out
''',
        fixed='''def slots(start: int, end: int, step: int) -> list[int]:
    """Slot start minutes covering the half-open window [start, end)."""
    out = []
    current = start
    while current + step <= end:
        out.append(current)
        current += step
    return out
''',
        base_cases=[[[0, 25, 10], [0, 10]], [[0, 5, 10], []]],
        edge_cases=[[[0, 30, 10], [0, 10, 20]], [[60, 120, 30], [60, 90]]],
        instruction=(
            "`sched.window.slots` drops the last slot whenever the window divides exactly by\n"
            "`step`, so a 30-minute window in 10-minute steps yields two slots instead of\n"
            "three. Include the final whole slot per the README."
        ),
    ),
    dict(
        id="bug-path-normalize",
        package="pathkit",
        module="norm",
        func="normalize",
        contract=(
            "`normalize(path)` collapses `.` and resolves `..` against the preceding\n"
            "segment, including a `..` in final position. A `..` that would escape the root\n"
            "is dropped."
        ),
        buggy='''def normalize(path: str) -> str:
    """Collapse '.' and resolve '..' in a slash-separated path."""
    out: list[str] = []
    segments = path.split("/")
    for index, segment in enumerate(segments):
        if segment in ("", "."):
            continue
        if segment == ".." and index < len(segments) - 1:
            if out:
                out.pop()
            continue
        out.append(segment)
    return "/".join(out)
''',
        fixed='''def normalize(path: str) -> str:
    """Collapse '.' and resolve '..' in a slash-separated path."""
    out: list[str] = []
    for segment in path.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if out:
                out.pop()
            continue
        out.append(segment)
    return "/".join(out)
''',
        base_cases=[[["a/./b/c"], "a/b/c"], [["a/../b/c"], "b/c"]],
        edge_cases=[[["a/b/.."], "a"], [["a/b/c/../.."], "a"]],
        instruction=(
            "`pathkit.norm.normalize` leaves a trailing `..` in the output instead of\n"
            "resolving it, so `a/b/..` normalizes to `a/b/..`. Resolve `..` wherever it\n"
            "appears, per the README."
        ),
    ),
    dict(
        id="bug-csv-quote",
        package="csvlite",
        module="quote",
        func="quote_field",
        contract=(
            "`quote_field(value)` wraps a field in double quotes when it contains a comma,\n"
            "a newline or a double quote, and doubles any embedded double quote."
        ),
        buggy='''def quote_field(value: str) -> str:
    """Quote *value* for a comma-separated line."""
    if "," in value or "\\n" in value:
        return '"' + value + '"'
    return value
''',
        fixed='''def quote_field(value: str) -> str:
    """Quote *value* for a comma-separated line."""
    if "," in value or "\\n" in value or '"' in value:
        return '"' + value.replace('"', '""') + '"'
    return value
''',
        base_cases=[[["plain"], "plain"], [["a,b"], '"a,b"']],
        edge_cases=[[['say "hi"'], '"say ""hi"""'], [['a,"b"'], '"a,""b"""']],
        instruction=(
            "`csvlite.quote.quote_field` neither quotes nor escapes a field containing a\n"
            "double quote, so the emitted line cannot be parsed back. Follow the README's\n"
            "escaping rule; the comma and newline cases already behave."
        ),
    ),
    dict(
        id="bug-version-compare",
        package="semver2",
        module="compare",
        func="compare_versions",
        contract=(
            "`compare_versions(a, b)` returns -1, 0 or 1 comparing dotted numeric versions\n"
            "segment by segment as INTEGERS, so 10 sorts after 9."
        ),
        buggy='''def compare_versions(a: str, b: str) -> int:
    """Compare dotted numeric versions; -1, 0 or 1."""
    left = a.split(".")
    right = b.split(".")
    for x, y in zip(left, right):
        if x != y:
            return -1 if x < y else 1
    if len(left) == len(right):
        return 0
    return -1 if len(left) < len(right) else 1
''',
        fixed='''def compare_versions(a: str, b: str) -> int:
    """Compare dotted numeric versions; -1, 0 or 1."""
    left = [int(part) for part in a.split(".")]
    right = [int(part) for part in b.split(".")]
    for x, y in zip(left, right):
        if x != y:
            return -1 if x < y else 1
    if len(left) == len(right):
        return 0
    return -1 if len(left) < len(right) else 1
''',
        base_cases=[[["1.2.3", "1.2.3"], 0], [["1.2.3", "1.3.0"], -1]],
        edge_cases=[[["1.10.0", "1.9.0"], 1], [["2.0.0", "10.0.0"], -1]],
        instruction=(
            "`semver2.compare.compare_versions` compares version segments as strings, so\n"
            "1.10.0 sorts before 1.9.0. Compare them numerically as the README specifies,\n"
            "keeping the -1/0/1 return contract."
        ),
    ),
    dict(
        id="bug-median",
        package="statkit",
        module="center",
        func="median",
        contract=(
            "`median(values)` returns the middle value of a sorted copy; for an\n"
            "even-length input it returns the mean of the two middle values as a float."
        ),
        buggy='''def median(values: list[float]) -> float:
    """The median of *values*."""
    ordered = sorted(values)
    return float(ordered[len(ordered) // 2])
''',
        fixed='''def median(values: list[float]) -> float:
    """The median of *values*."""
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2
''',
        base_cases=[[[[3, 1, 2]], 2.0], [[[5]], 5.0]],
        edge_cases=[[[[1, 2, 3, 4]], 2.5], [[[10, 20]], 15.0]],
        instruction=(
            "`statkit.center.median` returns the upper middle value for an even-length\n"
            "input instead of averaging the two middle values. Follow the README; the\n"
            "odd-length behaviour is already right."
        ),
    ),
    dict(
        id="bug-title-case",
        package="textkit",
        module="title",
        func="title_case",
        contract=(
            "`title_case(text)` upper-cases the first letter of every word, treating a\n"
            "hyphen as a word separator so `well-known` becomes `Well-Known`."
        ),
        buggy='''def title_case(text: str) -> str:
    """Capitalise the first letter of each word."""
    return " ".join(word[:1].upper() + word[1:] for word in text.split(" "))
''',
        fixed='''def title_case(text: str) -> str:
    """Capitalise the first letter of each word."""
    words = []
    for word in text.split(" "):
        parts = word.split("-")
        words.append("-".join(part[:1].upper() + part[1:] for part in parts))
    return " ".join(words)
''',
        base_cases=[[["hello world"], "Hello World"], [["a b"], "A B"]],
        edge_cases=[[["well-known issue"], "Well-Known Issue"], [["up-to-date"], "Up-To-Date"]],
        instruction=(
            "`textkit.title.title_case` capitalises only the first fragment of a hyphenated\n"
            "word, so `well-known` becomes `Well-known`. Treat the hyphen as a word\n"
            "separator per the README."
        ),
    ),
    dict(
        id="bug-first-index",
        package="searchkit",
        module="bisect",
        func="first_index",
        contract=(
            "`first_index(ordered, target)` returns the index of the FIRST occurrence of\n"
            "`target` in a sorted list, or -1 when it is absent."
        ),
        buggy='''def first_index(ordered: list[int], target: int) -> int:
    """Index of the first occurrence of *target*, or -1."""
    low, high = 0, len(ordered) - 1
    while low <= high:
        mid = (low + high) // 2
        if ordered[mid] == target:
            return mid
        if ordered[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
''',
        fixed='''def first_index(ordered: list[int], target: int) -> int:
    """Index of the first occurrence of *target*, or -1."""
    low, high = 0, len(ordered) - 1
    found = -1
    while low <= high:
        mid = (low + high) // 2
        if ordered[mid] == target:
            found = mid
            high = mid - 1
        elif ordered[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return found
''',
        base_cases=[[[[1, 2, 3, 4], 3], 2], [[[1, 2, 3], 9], -1]],
        edge_cases=[[[[1, 2, 2, 2, 3], 2], 1], [[[5, 5, 5], 5], 0]],
        instruction=(
            "`searchkit.bisect.first_index` returns whichever duplicate the search happens\n"
            "to land on rather than the first one. Return the first occurrence as the\n"
            "README specifies; the absent-target and unique-target cases already behave."
        ),
    ),
    dict(
        id="bug-money-round",
        package="moneykit",
        module="rounding",
        func="round_half_even",
        contract=(
            "`round_half_even(amount, places)` rounds to `places` decimals, breaking an\n"
            "exact half toward the EVEN neighbour: 2.5 -> 2, 3.5 -> 4."
        ),
        buggy='''def round_half_even(amount: float, places: int) -> float:
    """Round *amount* to *places* decimals, half to even."""
    scale = 10 ** places
    scaled = amount * scale
    whole = int(scaled)
    fraction = scaled - whole
    if fraction >= 0.5:
        whole += 1
    return whole / scale
''',
        fixed='''def round_half_even(amount: float, places: int) -> float:
    """Round *amount* to *places* decimals, half to even."""
    scale = 10 ** places
    scaled = amount * scale
    whole = int(scaled)
    fraction = scaled - whole
    if fraction > 0.5:
        whole += 1
    elif fraction == 0.5 and whole % 2 == 1:
        whole += 1
    return whole / scale
''',
        base_cases=[[[2.4, 0], 2.0], [[2.6, 0], 3.0]],
        edge_cases=[[[2.5, 0], 2.0], [[3.5, 0], 4.0], [[0.125, 2], 0.12]],
        instruction=(
            "`moneykit.rounding.round_half_even` rounds an exact half away from zero, so 2.5\n"
            "becomes 3 where the README requires the even neighbour. Implement the\n"
            "half-to-even rule; the non-half cases already behave."
        ),
    ),
    dict(
        id="bug-retry-backoff",
        package="retrykit",
        module="backoff",
        func="delays",
        contract=(
            "`delays(attempts, base)` lists the wait in seconds BETWEEN attempts, so\n"
            "`attempts` tries produce `attempts - 1` waits, doubling from `base`. No single\n"
            "wait ever exceeds `MAX_DELAY_S`."
        ),
        buggy='''MAX_DELAY_S = 30.0


def delays(attempts: int, base: float) -> list[float]:
    """Waits between *attempts* tries, doubling from *base*."""
    return [base * (2 ** i) for i in range(max(attempts - 1, 0))]
''',
        fixed='''MAX_DELAY_S = 30.0


def delays(attempts: int, base: float) -> list[float]:
    """Waits between *attempts* tries, doubling from *base*."""
    return [min(base * (2 ** i), MAX_DELAY_S) for i in range(max(attempts - 1, 0))]
''',
        base_cases=[[[3, 1.0], [1.0, 2.0]], [[1, 1.0], []]],
        edge_cases=[
            [[8, 1.0], [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0]],
            [[7, 5.0], [5.0, 10.0, 20.0, 30.0, 30.0, 30.0]],
        ],
        instruction=(
            "`retrykit.backoff.delays` lets the doubling run unbounded, so a long retry\n"
            "schedule asks the caller to wait minutes between attempts. Apply the\n"
            "`MAX_DELAY_S` ceiling the README states, keeping the number of waits and the\n"
            "doubling below the ceiling unchanged."
        ),
    ),
    dict(
        id="bug-flatten",
        package="treekit",
        module="flatten",
        func="flatten",
        contract=(
            "`flatten(items)` returns every non-list leaf in depth-first order. An empty\n"
            "nested list contributes nothing at all -- never a placeholder."
        ),
        buggy='''def flatten(items: list) -> list:
    """Depth-first leaves of a nested list."""
    out = []
    for item in items:
        if isinstance(item, list):
            inner = flatten(item)
            out.append(inner[0] if inner else None)
        else:
            out.append(item)
    return out
''',
        fixed='''def flatten(items: list) -> list:
    """Depth-first leaves of a nested list."""
    out = []
    for item in items:
        if isinstance(item, list):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out
''',
        base_cases=[[[[1, 2, 3]], [1, 2, 3]], [[[1, [2]]], [1, 2]]],
        edge_cases=[[[[1, [], 2]], [1, 2]], [[[1, [2, 3], 4]], [1, 2, 3, 4]]],
        instruction=(
            "`treekit.flatten.flatten` substitutes `None` for an empty nested list and keeps\n"
            "only the first leaf of a longer one, so leaves go missing and placeholders\n"
            "appear. Return every leaf in order per the README."
        ),
    ),
    dict(
        id="bug-slug",
        package="textkit",
        module="slug",
        func="slugify",
        contract=(
            "`slugify(text)` lower-cases, replaces each run of non-alphanumerics with a\n"
            "single hyphen, and strips leading and trailing hyphens."
        ),
        buggy='''def slugify(text: str) -> str:
    """Lower-case slug with single hyphens between words."""
    out = []
    for char in text.lower():
        out.append(char if char.isalnum() else "-")
    return "".join(out).strip("-")
''',
        fixed='''def slugify(text: str) -> str:
    """Lower-case slug with single hyphens between words."""
    out = []
    previous_sep = False
    for char in text.lower():
        if char.isalnum():
            out.append(char)
            previous_sep = False
        elif not previous_sep:
            out.append("-")
            previous_sep = True
    return "".join(out).strip("-")
''',
        base_cases=[[["Hello World"], "hello-world"], [["  edges  "], "edges"]],
        edge_cases=[[["a -- b"], "a-b"], [["Report: Q3, final"], "report-q3-final"]],
        instruction=(
            "`textkit.slug.slugify` emits one hyphen per separator character instead of one\n"
            "per run, so `a -- b` becomes `a----b`. Collapse each run to a single hyphen as\n"
            "the README describes; the trimming already behaves."
        ),
    ),
    dict(
        id="bug-column-width",
        package="tablekit",
        module="width",
        func="column_widths",
        contract=(
            "`column_widths(header, rows)` returns the display width of each column: the\n"
            "longest cell in that column, counting the HEADER cell too."
        ),
        buggy='''def column_widths(header: list[str], rows: list[list[str]]) -> list[int]:
    """Longest cell per column, header included."""
    widths = [0] * len(header)
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    return widths
''',
        fixed='''def column_widths(header: list[str], rows: list[list[str]]) -> list[int]:
    """Longest cell per column, header included."""
    widths = [len(cell) for cell in header]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    return widths
''',
        base_cases=[[[["id"], [["12345"]]], [5]], [[["ab"], [["xyz"]]], [3]]],
        edge_cases=[
            [[["identifier"], [["12"]]], [10]],
            [[["a", "region"], [["xx", "eu"]]], [2, 6]],
        ],
        instruction=(
            "`tablekit.width.column_widths` ignores the header row, so a column whose header\n"
            "is wider than every value comes back too narrow and the rendered table breaks.\n"
            "Count the header cell as the README requires."
        ),
    ),
    dict(
        id="bug-parse-duration",
        package="durationkit",
        module="parse",
        func="parse_duration",
        contract=(
            "`parse_duration(text)` parses `<n>h<n>m<n>s` shorthand into whole seconds.\n"
            "A component written as zero counts as present and contributes zero."
        ),
        buggy='''import re

_PATTERN = re.compile(r"(\\d+)([hms])")
_UNITS = {"h": 3600, "m": 60, "s": 1}


def parse_duration(text: str) -> int:
    """Whole seconds for a <n>h<n>m<n>s duration string."""
    total = 0
    for amount, unit in _PATTERN.findall(text):
        value = int(amount)
        if not value:
            continue
        total += value * _UNITS[unit]
    return total
''',
        fixed='''import re

_PATTERN = re.compile(r"(\\d+)([hms])")
_UNITS = {"h": 3600, "m": 60, "s": 1}


def parse_duration(text: str) -> int:
    """Whole seconds for a <n>h<n>m<n>s duration string."""
    total = 0
    matches = _PATTERN.findall(text)
    if not matches:
        raise ValueError(f"not a duration: {text!r}")
    for amount, unit in matches:
        total += int(amount) * _UNITS[unit]
    return total
''',
        base_cases=[[["1h30m"], 5400], [["45s"], 45]],
        edge_cases=[[["0h5m"], 300], [[""], {"raises": "ValueError"}]],
        instruction=(
            "`durationkit.parse.parse_duration` skips any component written as zero and\n"
            "returns 0 for a string that is not a duration at all, so a malformed input is\n"
            "indistinguishable from a genuine zero. Count zero components, and raise\n"
            "`ValueError` when the text contains no duration component, per the README."
        ),
    ),
    dict(
        id="bug-ordinal",
        package="textkit",
        module="ordinal",
        func="ordinal",
        contract=(
            "`ordinal(n)` renders an English ordinal suffix. The teens 11, 12 and 13 take\n"
            "`th`, not `st`/`nd`/`rd`."
        ),
        buggy='''SUFFIXES = {1: "st", 2: "nd", 3: "rd"}


def ordinal(n: int) -> str:
    """English ordinal for *n*, e.g. 1 -> '1st'."""
    return f"{n}{SUFFIXES.get(n % 10, 'th')}"
''',
        fixed='''SUFFIXES = {1: "st", 2: "nd", 3: "rd"}


def ordinal(n: int) -> str:
    """English ordinal for *n*, e.g. 1 -> '1st'."""
    if n % 100 in (11, 12, 13):
        return f"{n}th"
    return f"{n}{SUFFIXES.get(n % 10, 'th')}"
''',
        base_cases=[[[1], "1st"], [[22], "22nd"], [[5], "5th"]],
        edge_cases=[[[11], "11th"], [[12], "12th"], [[113], "113th"]],
        instruction=(
            "`textkit.ordinal.ordinal` gives the teens the wrong suffix, so 11 renders as\n"
            "`11st`. Apply the teens exception the README states; the other cases already\n"
            "behave."
        ),
    ),
]
