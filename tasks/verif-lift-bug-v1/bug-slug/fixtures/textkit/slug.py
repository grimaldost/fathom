def slugify(text: str) -> str:
    """Lower-case slug with single hyphens between words."""
    out = []
    for char in text.lower():
        out.append(char if char.isalnum() else "-")
    return "".join(out).strip("-")
