def is_valid(digits: str) -> bool:
    """Mod-10 checksum: double every second digit counting from the right."""
    total = 0
    for index, char in enumerate(digits):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0
