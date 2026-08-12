def normalize(path: str) -> str:
    """Collapse '.' and resolve '..' in a slash-separated path."""
    out: list[str] = []
    segments = path.split("/")
    for index, segment in enumerate(segments):
        if segment in ("", "."):
            continue
        if segment == ".." and index < len(segments) - 1:
            if out:
                out.pop()
            continue
        out.append(segment)
    return "/".join(out)
