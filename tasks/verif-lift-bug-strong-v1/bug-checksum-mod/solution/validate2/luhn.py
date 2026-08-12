def is_valid(digits: str) -> bool:
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
