def cohort_sizes(users: list[dict], events: list[dict], *, strict: bool = False) -> dict:
    """Distinct active users per cohort."""
    cohort_of = {user["id"]: user["cohort"] for user in users}
    seen: dict = {}
    for user in users:
        seen.setdefault(user["cohort"], set())
    for event in events:
        cohort = cohort_of.get(event["user_id"])
        if cohort is None:
            continue
        seen[cohort].add(event["user_id"])
    return {cohort: len(members) for cohort, members in seen.items()}
