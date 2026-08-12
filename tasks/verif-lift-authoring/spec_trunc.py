"""TRUNC class: the same defect twice in one module -- once inside the line range the
instruction cites, once past its end.

The instruction points a reader at a symptom location as a line range; the defect is
a property of the module, and the README says so.  A candidate who reads the cited
slice and stops fixes the first occurrence and leaves the twin.  ``spec_met`` scores
the in-slice occurrence (the anchor, expected to saturate);
``defect_past_slice_handled`` scores the twin and is the primary.

The cited range is not hand-written: ``generate.py`` locates the second function in
the generated module and cites a range ending several lines BEFORE it, so the claim
"the twin is past the cited slice" is true of the file that actually ships.

There is no footprint criterion here.  Per the plan this class is never pooled with
the footprint classes -- it asks a perception question, not an act question.
"""

from __future__ import annotations

TRUNC = [
    dict(
        id="trunc-pct-format",
        package="reportkit",
        module="summary",
        func="format_share",
        func_past_slice="format_delta",
        contract=(
            "Percentages in this module round HALF UP at one decimal place, in\n"
            "`format_share` and in `format_delta` alike -- the two renderers must agree or\n"
            "a share and its delta disagree in the same table row."
        ),
        head='''"""Rendering helpers for the summary table."""

SUFFIX = "%"
PLACES = 1
_SCALE = 10 ** PLACES
''',
        buggy_a='''def format_share(value: float) -> str:
    """Render *value* (0..1) as a percentage string."""
    percent = value * 100.0
    return f"{int(percent * _SCALE) / _SCALE:.1f}{SUFFIX}"
''',
        fixed_a='''def format_share(value: float) -> str:
    """Render *value* (0..1) as a percentage string."""
    percent = value * 100.0
    return f"{_round_half_up(percent):.1f}{SUFFIX}"
''',
        middle='''
def _round_half_up(percent: float) -> float:
    """Round *percent* to PLACES decimals, halves going up."""
    scaled = percent * _SCALE
    whole = int(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    return whole / _SCALE


def sign_of(value: float) -> str:
    """The sign marker a delta carries in the table."""
    if value > 0:
        return "+"
    if value < 0:
        return "-"
    return ""


def width_for(cells: list) -> int:
    """Column width for a rendered percentage column."""
    return max((len(str(cell)) for cell in cells), default=0)

''',
        buggy_b='''def format_delta(value: float) -> str:
    """Render a signed change *value* (0..1) as a percentage string."""
    percent = abs(value) * 100.0
    body = f"{int(percent * _SCALE) / _SCALE:.1f}{SUFFIX}"
    return f"{sign_of(value)}{body}"
''',
        fixed_b='''def format_delta(value: float) -> str:
    """Render a signed change *value* (0..1) as a percentage string."""
    percent = abs(value) * 100.0
    body = f"{_round_half_up(percent):.1f}{SUFFIX}"
    return f"{sign_of(value)}{body}"
''',
        base_cases=[[[0.12], "12.0%"], [[0.5], "50.0%"]],
        edge_cases=[[[0.1235], "12.4%"], [[0.4445], "44.5%"]],
        past_slice_base=[[[0.12], "+12.0%"]],
        past_slice_cases=[[[0.1235], "+12.4%"], [[-0.4445], "-44.5%"]],
        symptom=("a share renders as 12.3% where 12.4% is expected"),
    ),
    dict(
        id="trunc-escape-cell",
        package="tablerender",
        module="escape",
        func="escape_cell",
        func_past_slice="escape_header",
        contract=(
            "Every rendered cell escapes the pipe character as `\\\\|` so a value cannot break\n"
            "the table layout. Both `escape_cell` and `escape_header` apply the rule; a\n"
            "header is as capable of containing a pipe as a body cell."
        ),
        head='''"""Escaping for pipe-delimited table rendering."""

PIPE = "|"
ESCAPED_PIPE = "\\\\|"
''',
        buggy_a='''def escape_cell(value: str) -> str:
    """Escape a body cell for the pipe-delimited renderer."""
    return value.strip()
''',
        fixed_a='''def escape_cell(value: str) -> str:
    """Escape a body cell for the pipe-delimited renderer."""
    return value.strip().replace(PIPE, ESCAPED_PIPE)
''',
        middle='''
def pad(value: str, width: int) -> str:
    """Pad *value* to *width* for a fixed-width column."""
    return value + " " * max(width - len(value), 0)


def join_row(cells: list) -> str:
    """Join already-escaped *cells* into one rendered row."""
    return PIPE + PIPE.join(cells) + PIPE


def rule(widths: list) -> str:
    """The dashed rule under a header row."""
    return PIPE + PIPE.join("-" * width for width in widths) + PIPE

''',
        buggy_b='''def escape_header(value: str) -> str:
    """Escape a header cell for the pipe-delimited renderer."""
    return value.strip().upper()
''',
        fixed_b='''def escape_header(value: str) -> str:
    """Escape a header cell for the pipe-delimited renderer."""
    return value.strip().upper().replace(PIPE, ESCAPED_PIPE)
''',
        base_cases=[[["  plain  "], "plain"]],
        edge_cases=[[["a|b"], "a\\|b"], [[" x|y|z "], "x\\|y\\|z"]],
        past_slice_base=[[["  name  "], "NAME"]],
        past_slice_cases=[[["a|b"], "A\\|B"], [["left|right"], "LEFT\\|RIGHT"]],
        symptom="a value containing a pipe splits into two columns",
    ),
    dict(
        id="trunc-clamp-score",
        package="scoring",
        module="clamp",
        func="clamp_score",
        func_past_slice="clamp_weight",
        contract=(
            "Both clamps in this module are INCLUSIVE at the bounds and clamp rather than\n"
            "reject: a value below the low bound becomes the low bound, one above the high\n"
            "bound becomes the high bound. `clamp_score` and `clamp_weight` differ only in\n"
            "their bounds."
        ),
        head='''"""Bounded score and weight coercion."""

SCORE_LOW = 0.0
SCORE_HIGH = 100.0
WEIGHT_LOW = 0.0
WEIGHT_HIGH = 1.0
''',
        buggy_a='''def clamp_score(value: float) -> float:
    """Coerce *value* into the score range."""
    if value < SCORE_LOW:
        return SCORE_LOW
    return value
''',
        fixed_a='''def clamp_score(value: float) -> float:
    """Coerce *value* into the score range."""
    if value < SCORE_LOW:
        return SCORE_LOW
    if value > SCORE_HIGH:
        return SCORE_HIGH
    return value
''',
        middle='''
def score_band(value: float) -> str:
    """The reporting band a clamped score falls in."""
    if value >= 80.0:
        return "high"
    if value >= 40.0:
        return "mid"
    return "low"


def normalise(value: float, low: float, high: float) -> float:
    """Position of *value* within [low, high] as a 0..1 fraction."""
    span = high - low
    return 0.0 if span == 0 else (value - low) / span


def describe(value: float) -> str:
    """One-line description of a clamped score."""
    return f"{value:.1f} ({score_band(value)})"

''',
        buggy_b='''def clamp_weight(value: float) -> float:
    """Coerce *value* into the weight range."""
    if value < WEIGHT_LOW:
        return WEIGHT_LOW
    return value
''',
        fixed_b='''def clamp_weight(value: float) -> float:
    """Coerce *value* into the weight range."""
    if value < WEIGHT_LOW:
        return WEIGHT_LOW
    if value > WEIGHT_HIGH:
        return WEIGHT_HIGH
    return value
''',
        base_cases=[[[-5.0], 0.0], [[50.0], 50.0]],
        edge_cases=[[[140.0], 100.0], [[100.5], 100.0]],
        past_slice_base=[[[-0.5], 0.0], [[0.25], 0.25]],
        past_slice_cases=[[[1.4], 1.0], [[2.0], 1.0]],
        symptom="a score of 140 is reported unclamped",
    ),
    dict(
        id="trunc-trim-label",
        package="labels",
        module="trim",
        func="trim_label",
        func_past_slice="trim_note",
        contract=(
            "Truncation in this module always leaves room for the ellipsis: the returned\n"
            "string is never longer than the requested limit, ellipsis included. The rule\n"
            "holds for `trim_label` and for `trim_note`."
        ),
        head='''"""Length-bounded label and note rendering."""

ELLIPSIS = "..."
''',
        buggy_a='''def trim_label(text: str, limit: int) -> str:
    """Shorten *text* to at most *limit* characters."""
    if len(text) <= limit:
        return text
    return text[:limit] + ELLIPSIS
''',
        fixed_a='''def trim_label(text: str, limit: int) -> str:
    """Shorten *text* to at most *limit* characters."""
    if len(text) <= limit:
        return text
    return text[: max(limit - len(ELLIPSIS), 0)] + ELLIPSIS
''',
        middle='''
def fits(text: str, limit: int) -> bool:
    """Whether *text* already fits within *limit*."""
    return len(text) <= limit


def budget(limit: int) -> int:
    """Characters available once the ellipsis is reserved."""
    return max(limit - len(ELLIPSIS), 0)


def longest(items: list) -> int:
    """Length of the longest item, for column sizing."""
    return max((len(item) for item in items), default=0)

''',
        buggy_b='''def trim_note(text: str, limit: int) -> str:
    """Shorten a multi-word note to at most *limit* characters."""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + ELLIPSIS
''',
        fixed_b='''def trim_note(text: str, limit: int) -> str:
    """Shorten a multi-word note to at most *limit* characters."""
    if len(text) <= limit:
        return text
    return text[: budget(limit)].rstrip() + ELLIPSIS
''',
        base_cases=[[["short", 10], "short"]],
        edge_cases=[[["abcdefghij", 6], "abc..."], [["longer text", 5], "lo..."]],
        past_slice_base=[[["ok", 10], "ok"]],
        past_slice_cases=[[["abcdefghij", 6], "abc..."], [["a note here", 8], "a not..."]],
        symptom="a label rendered with limit 6 comes back 9 characters long",
    ),
    dict(
        id="trunc-plural",
        package="phrasing",
        module="plural",
        func="plural_items",
        func_past_slice="plural_errors",
        contract=(
            "Counted nouns in this module read `1 item` and `0 items` -- only a count of\n"
            "exactly one takes the singular. Both `plural_items` and `plural_errors` follow\n"
            "the rule, including for negative counts, which are plural."
        ),
        head='''"""Count-aware noun phrases for report lines."""

ITEM = ("item", "items")
ERROR = ("error", "errors")
''',
        buggy_a='''def plural_items(count: int) -> str:
    """Render a count of items as a noun phrase."""
    word = ITEM[0] if count <= 1 else ITEM[1]
    return f"{count} {word}"
''',
        fixed_a='''def plural_items(count: int) -> str:
    """Render a count of items as a noun phrase."""
    word = ITEM[0] if count == 1 else ITEM[1]
    return f"{count} {word}"
''',
        middle='''
def pick(count: int, forms: tuple) -> str:
    """The form of *forms* matching *count*."""
    return forms[0] if count == 1 else forms[1]


def join_phrases(phrases: list) -> str:
    """Join rendered phrases into one sentence fragment."""
    if not phrases:
        return ""
    if len(phrases) == 1:
        return phrases[0]
    return ", ".join(phrases[:-1]) + " and " + phrases[-1]


def emphasise(phrase: str, loud: bool) -> str:
    """Optionally emphasise a rendered phrase."""
    return phrase.upper() if loud else phrase

''',
        buggy_b='''def plural_errors(count: int) -> str:
    """Render a count of errors as a noun phrase."""
    word = ERROR[0] if count <= 1 else ERROR[1]
    return f"{count} {word}"
''',
        fixed_b='''def plural_errors(count: int) -> str:
    """Render a count of errors as a noun phrase."""
    return f"{count} {pick(count, ERROR)}"
''',
        base_cases=[[[1], "1 item"], [[3], "3 items"]],
        edge_cases=[[[0], "0 items"], [[-2], "-2 items"]],
        past_slice_base=[[[1], "1 error"], [[4], "4 errors"]],
        past_slice_cases=[[[0], "0 errors"], [[-1], "-1 errors"]],
        symptom="a summary line reads '0 item'",
    ),
    dict(
        id="trunc-currency",
        package="amounts",
        module="money",
        func="fmt_amount",
        func_past_slice="fmt_total",
        contract=(
            "Amounts in this module are stored in minor units and rendered with two\n"
            "decimals and a thousands separator. `fmt_amount` and `fmt_total` render the\n"
            "same way; a total that disagrees with its parts is a rendering defect."
        ),
        head='''"""Minor-unit amount rendering."""

MINOR_PER_MAJOR = 100
SEPARATOR = ","
''',
        buggy_a='''def fmt_amount(minor: int) -> str:
    """Render *minor* units as a major-unit amount."""
    return f"{minor / MINOR_PER_MAJOR:.2f}"
''',
        fixed_a='''def fmt_amount(minor: int) -> str:
    """Render *minor* units as a major-unit amount."""
    return f"{minor / MINOR_PER_MAJOR:,.2f}".replace(",", SEPARATOR)
''',
        middle='''
def to_major(minor: int) -> float:
    """Major units for *minor*."""
    return minor / MINOR_PER_MAJOR


def group_digits(text: str) -> str:
    """Insert SEPARATOR every three digits of an integer part."""
    whole, _, fraction = text.partition(".")
    grouped = f"{int(whole):,}".replace(",", SEPARATOR)
    return f"{grouped}.{fraction}" if fraction else grouped


def is_negative(minor: int) -> bool:
    """Whether an amount renders with a leading minus."""
    return minor < 0

''',
        buggy_b='''def fmt_total(minors: list) -> str:
    """Render the total of *minors* as a major-unit amount."""
    return f"{sum(minors) / MINOR_PER_MAJOR:.2f}"
''',
        fixed_b='''def fmt_total(minors: list) -> str:
    """Render the total of *minors* as a major-unit amount."""
    return group_digits(f"{sum(minors) / MINOR_PER_MAJOR:.2f}")
''',
        base_cases=[[[1234], "12.34"], [[5], "0.05"]],
        edge_cases=[[[123456789], "1,234,567.89"], [[100000], "1,000.00"]],
        past_slice_base=[[[[1234]], "12.34"]],
        past_slice_cases=[[[[123456789]], "1,234,567.89"], [[[100000, 0]], "1,000.00"]],
        symptom="a large amount renders without thousands separators",
    ),
    dict(
        id="trunc-date-range",
        package="calendars",
        module="dates",
        func="fmt_day",
        func_past_slice="fmt_range",
        contract=(
            "Dates in this module render zero-padded as `YYYY-MM-DD`. `fmt_day` renders one\n"
            "date and `fmt_range` renders two joined by ` to `; both pad, so the two never\n"
            "disagree about the same day."
        ),
        head='''"""Date rendering for report headers."""

JOINER = " to "
''',
        buggy_a='''def fmt_day(year: int, month: int, day: int) -> str:
    """Render one date as YYYY-MM-DD."""
    return f"{year}-{month}-{day}"
''',
        fixed_a='''def fmt_day(year: int, month: int, day: int) -> str:
    """Render one date as YYYY-MM-DD."""
    return f"{year:04d}-{month:02d}-{day:02d}"
''',
        middle='''
def pad2(value: int) -> str:
    """Two-digit zero-padded rendering of *value*."""
    return f"{value:02d}"


def is_end_of_month(month: int, day: int) -> bool:
    """Rough end-of-month test used by the header renderer."""
    return day >= (30 if month in (4, 6, 9, 11) else 31)


def label_for(month: int) -> str:
    """Short month label used beside a rendered range."""
    names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return names[month] if 1 <= month <= 12 else "?"

''',
        buggy_b='''def fmt_range(start: list, end: list) -> str:
    """Render a date range as 'YYYY-MM-DD to YYYY-MM-DD'."""
    left = f"{start[0]}-{start[1]}-{start[2]}"
    right = f"{end[0]}-{end[1]}-{end[2]}"
    return f"{left}{JOINER}{right}"
''',
        fixed_b='''def fmt_range(start: list, end: list) -> str:
    """Render a date range as 'YYYY-MM-DD to YYYY-MM-DD'."""
    left = fmt_day(start[0], start[1], start[2])
    right = fmt_day(end[0], end[1], end[2])
    return f"{left}{JOINER}{right}"
''',
        base_cases=[[[2026, 11, 30], "2026-11-30"]],
        edge_cases=[[[2026, 1, 5], "2026-01-05"], [[2026, 9, 9], "2026-09-09"]],
        past_slice_base=[[[[2026, 11, 30], [2026, 12, 31]], "2026-11-30 to 2026-12-31"]],
        past_slice_cases=[
            [[[2026, 1, 5], [2026, 2, 9]], "2026-01-05 to 2026-02-09"],
            [[[2026, 3, 1], [2026, 3, 9]], "2026-03-01 to 2026-03-09"],
        ],
        symptom="a January date renders as 2026-1-5",
    ),
    dict(
        id="trunc-sort-key",
        package="ordering",
        module="sortkeys",
        func="sort_key_name",
        func_past_slice="sort_key_group",
        contract=(
            "Sort keys in this module are case-insensitive and ignore leading whitespace, so\n"
            "the rendered order does not depend on how a value was typed. `sort_key_name`\n"
            "and `sort_key_group` build their keys the same way."
        ),
        head='''"""Sort key construction for the rendered listing."""

FALLBACK = "\\uffff"
''',
        buggy_a='''def sort_key_name(value: str) -> str:
    """Sort key for a name column."""
    return value.strip() or FALLBACK
''',
        fixed_a='''def sort_key_name(value: str) -> str:
    """Sort key for a name column."""
    return value.strip().casefold() or FALLBACK
''',
        middle='''
def normalise(value: str) -> str:
    """The comparable spelling of a cell value."""
    return value.strip().casefold()


def missing_last(key: str) -> str:
    """Push an empty key to the end of the listing."""
    return key or FALLBACK


def compare(left: str, right: str) -> int:
    """Three-way comparison of two prepared sort keys."""
    if left == right:
        return 0
    return -1 if left < right else 1

''',
        buggy_b='''def sort_key_group(value: str) -> str:
    """Sort key for a group column."""
    return value.strip() or FALLBACK
''',
        fixed_b='''def sort_key_group(value: str) -> str:
    """Sort key for a group column."""
    return missing_last(normalise(value))
''',
        base_cases=[[["beta"], "beta"], [["   "], "￿"]],
        edge_cases=[[["Beta"], "beta"], [["  ALPHA "], "alpha"]],
        past_slice_base=[[["west"], "west"], [[""], "￿"]],
        past_slice_cases=[[["West"], "west"], [[" NORTH "], "north"]],
        symptom="'Beta' sorts before 'alpha' in the listing",
    ),
    dict(
        id="trunc-bounds",
        package="ranges",
        module="bounds",
        func="lower_bound",
        func_past_slice="upper_bound",
        contract=(
            "Both bound helpers treat the interval as CLOSED: `lower_bound` returns the\n"
            "first index whose value is >= the target, `upper_bound` the last index whose\n"
            "value is <= it. An empty list yields -1 from either."
        ),
        head='''"""Closed-interval index helpers over a sorted list."""

NOT_FOUND = -1
''',
        buggy_a='''def lower_bound(ordered: list, target: float) -> int:
    """First index whose value is >= *target*."""
    for index, value in enumerate(ordered):
        if value > target:
            return index
    return NOT_FOUND
''',
        fixed_a='''def lower_bound(ordered: list, target: float) -> int:
    """First index whose value is >= *target*."""
    for index, value in enumerate(ordered):
        if value >= target:
            return index
    return NOT_FOUND
''',
        middle='''
def is_empty(ordered: list) -> bool:
    """Whether there is nothing to search."""
    return not ordered


def span(ordered: list) -> float:
    """Distance between the extremes of a sorted list."""
    return 0.0 if is_empty(ordered) else ordered[-1] - ordered[0]


def clamp_index(index: int, ordered: list) -> int:
    """Keep *index* inside the list, or NOT_FOUND."""
    if is_empty(ordered):
        return NOT_FOUND
    return max(0, min(index, len(ordered) - 1))

''',
        buggy_b='''def upper_bound(ordered: list, target: float) -> int:
    """Last index whose value is <= *target*."""
    found = NOT_FOUND
    for index, value in enumerate(ordered):
        if value < target:
            found = index
    return found
''',
        fixed_b='''def upper_bound(ordered: list, target: float) -> int:
    """Last index whose value is <= *target*."""
    found = NOT_FOUND
    for index, value in enumerate(ordered):
        if value <= target:
            found = index
    return found
''',
        base_cases=[[[[1, 3, 5], 2], 1], [[[], 4], -1]],
        edge_cases=[[[[1, 3, 5], 3], 1], [[[2, 4], 2], 0]],
        past_slice_base=[[[[1, 3, 5], 4], 1], [[[], 4], -1]],
        past_slice_cases=[[[[1, 3, 5], 3], 1], [[[2, 4], 4], 1]],
        symptom="a target that equals a stored value is skipped",
    ),
    dict(
        id="trunc-safe-ratio",
        package="ratios",
        module="ratio",
        func="safe_ratio",
        func_past_slice="safe_growth",
        contract=(
            "A ratio with a zero denominator is undefined and returns `None` in this\n"
            "module -- never zero, which a consumer cannot tell from a real zero. Both\n"
            "`safe_ratio` and `safe_growth` obey it."
        ),
        head='''"""Ratio helpers that refuse to invent a value."""

PLACES = 4
''',
        buggy_a='''def safe_ratio(numerator: float, denominator: float):
    """Ratio of *numerator* to *denominator*, or None when undefined."""
    if not denominator:
        return 0.0
    return round(numerator / denominator, PLACES)
''',
        fixed_a='''def safe_ratio(numerator: float, denominator: float):
    """Ratio of *numerator* to *denominator*, or None when undefined."""
    if not denominator:
        return None
    return round(numerator / denominator, PLACES)
''',
        middle='''
def defined(value) -> bool:
    """Whether a computed ratio carries a value."""
    return value is not None


def as_percent(value):
    """Render a ratio as a percentage, preserving the undefined marker."""
    return None if value is None else round(value * 100.0, PLACES)


def worst(values: list):
    """The smallest defined ratio in *values*, or None."""
    defined_values = [value for value in values if value is not None]
    return min(defined_values) if defined_values else None

''',
        buggy_b='''def safe_growth(previous: float, current: float):
    """Growth of *current* over *previous*, or None when undefined."""
    if not previous:
        return 0.0
    return round((current - previous) / previous, PLACES)
''',
        fixed_b='''def safe_growth(previous: float, current: float):
    """Growth of *current* over *previous*, or None when undefined."""
    if not previous:
        return None
    return round((current - previous) / previous, PLACES)
''',
        base_cases=[[[1.0, 4.0], 0.25], [[3.0, 6.0], 0.5]],
        edge_cases=[[[1.0, 0.0], None], [[0.0, 0.0], None]],
        past_slice_base=[[[4.0, 5.0], 0.25]],
        past_slice_cases=[[[0.0, 5.0], None], [[0.0, 0.0], None]],
        symptom="an undefined ratio is reported as 0.0",
    ),
    dict(
        id="trunc-abbrev",
        package="units",
        module="abbrev",
        func="abbrev_count",
        func_past_slice="abbrev_bytes",
        contract=(
            "Abbreviation in this module rounds to one decimal and drops a trailing `.0`,\n"
            "so 1000 reads `1k` and 1500 reads `1.5k`. `abbrev_count` and `abbrev_bytes`\n"
            "share the rule; only their unit ladders differ."
        ),
        head='''"""Short renderings for large numbers."""

COUNT_STEPS = [(1_000_000_000, "b"), (1_000_000, "m"), (1_000, "k")]
BYTE_STEPS = [(1024 ** 3, "GiB"), (1024 ** 2, "MiB"), (1024, "KiB")]
''',
        buggy_a='''def abbrev_count(value: int) -> str:
    """Render a count in short form."""
    for step, suffix in COUNT_STEPS:
        if value >= step:
            return f"{round(value / step, 1)}{suffix}"
    return str(value)
''',
        fixed_a='''def abbrev_count(value: int) -> str:
    """Render a count in short form."""
    for step, suffix in COUNT_STEPS:
        if value >= step:
            return f"{_trim(round(value / step, 1))}{suffix}"
    return str(value)
''',
        middle='''
def _trim(number: float) -> str:
    """Render *number* without a trailing '.0'."""
    text = f"{number:.1f}"
    return text[:-2] if text.endswith(".0") else text


def ladder_for(kind: str) -> list:
    """The unit ladder a renderer should walk."""
    return BYTE_STEPS if kind == "bytes" else COUNT_STEPS


def fits_plain(value: int, kind: str) -> bool:
    """Whether *value* renders without abbreviation."""
    return value < ladder_for(kind)[-1][0]

''',
        buggy_b='''def abbrev_bytes(value: int) -> str:
    """Render a byte count in short form."""
    for step, suffix in BYTE_STEPS:
        if value >= step:
            return f"{round(value / step, 1)}{suffix}"
    return f"{value}B"
''',
        fixed_b='''def abbrev_bytes(value: int) -> str:
    """Render a byte count in short form."""
    for step, suffix in BYTE_STEPS:
        if value >= step:
            return f"{_trim(round(value / step, 1))}{suffix}"
    return f"{value}B"
''',
        base_cases=[[[1500], "1.5k"], [[42], "42"]],
        edge_cases=[[[1000], "1k"], [[2000000], "2m"]],
        past_slice_base=[[[1536], "1.5KiB"], [[42], "42B"]],
        past_slice_cases=[[[1024], "1KiB"], [[2097152], "2MiB"]],
        symptom="a count of 1000 renders as '1.0k'",
    ),
]
