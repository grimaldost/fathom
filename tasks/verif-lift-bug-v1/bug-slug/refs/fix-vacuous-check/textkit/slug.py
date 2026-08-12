def slugify(text: str) -> str:
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
