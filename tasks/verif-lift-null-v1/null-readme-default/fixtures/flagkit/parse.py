"""Flag parsing with defaults."""

DEFAULT_TIMEOUT_S = 30


def parse_flags(argv: list) -> dict:
    """Parse ``--name=value`` flags, filling in the timeout default."""
    flags = {"timeout_s": DEFAULT_TIMEOUT_S}
    for token in argv:
        if not token.startswith("--"):
            continue
        name, _, value = token[2:].partition("=")
        flags[name.replace("-", "_")] = int(value) if value.isdigit() else value
    return flags
