def top_k(rows: list[dict], k: int) -> list[dict]:
    """The *k* highest-scoring rows, highest first."""
    ordered = sorted(rows, key=lambda row: row["score"], reverse=True)
    return ordered[:k]
