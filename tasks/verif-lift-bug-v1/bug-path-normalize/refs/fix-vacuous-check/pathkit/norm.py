def normalize(path: str) -> str:
    """Collapse '.' and resolve '..' in a slash-separated path."""
    out: list[str] = []
    for segment in path.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if out:
                out.pop()
            continue
        out.append(segment)
    return "/".join(out)
