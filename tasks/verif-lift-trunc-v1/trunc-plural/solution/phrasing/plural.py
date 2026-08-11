"""Count-aware noun phrases for report lines."""

ITEM = ("item", "items")
ERROR = ("error", "errors")

def plural_items(count: int) -> str:
    """Render a count of items as a noun phrase."""
    word = ITEM[0] if count == 1 else ITEM[1]
    return f"{count} {word}"

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


def plural_errors(count: int) -> str:
    """Render a count of errors as a noun phrase."""
    return f"{count} {pick(count, ERROR)}"
