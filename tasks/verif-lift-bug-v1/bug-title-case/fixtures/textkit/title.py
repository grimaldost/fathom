def title_case(text: str) -> str:
    """Capitalise the first letter of each word."""
    return " ".join(word[:1].upper() + word[1:] for word in text.split(" "))
