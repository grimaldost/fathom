def title_case(text: str, *, strict: bool = False) -> str:
    """Capitalise the first letter of each word."""
    words = []
    for word in text.split(" "):
        parts = word.split("-")
        words.append("-".join(part[:1].upper() + part[1:] for part in parts))
    return " ".join(words)
