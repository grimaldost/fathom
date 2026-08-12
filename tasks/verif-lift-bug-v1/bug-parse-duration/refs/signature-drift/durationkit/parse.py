import re

_PATTERN = re.compile(r"(\d+)([hms])")
_UNITS = {"h": 3600, "m": 60, "s": 1}


def parse_duration(text: str, *, strict: bool = False) -> int:
    """Whole seconds for a <n>h<n>m<n>s duration string."""
    total = 0
    matches = _PATTERN.findall(text)
    if not matches:
        raise ValueError(f"not a duration: {text!r}")
    for amount, unit in matches:
        total += int(amount) * _UNITS[unit]
    return total
