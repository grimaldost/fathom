import re

_PATTERN = re.compile(r"(\d+)([hms])")
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
