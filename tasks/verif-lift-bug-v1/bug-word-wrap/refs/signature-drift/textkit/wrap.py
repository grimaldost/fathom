def wrap_words(text: str, width: int, *, strict: bool = False) -> list[str]:
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
