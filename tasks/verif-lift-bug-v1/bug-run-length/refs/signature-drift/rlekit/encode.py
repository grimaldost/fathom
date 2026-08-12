def encode_runs(text: str, *, strict: bool = False) -> list[list]:
    """Run-length encode *text* as [char, count] pairs."""
    runs: list[list] = []
    previous = ""
    count = 0
    for char in text:
        if char == previous:
            count += 1
        else:
            if previous:
                runs.append([previous, count])
            previous = char
            count = 1
    if previous:
        runs.append([previous, count])
    return runs
