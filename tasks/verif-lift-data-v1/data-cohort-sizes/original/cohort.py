def cohort_sizes(users: list[dict], events: list[dict]) -> dict:
    """Distinct active users per cohort."""
    cohort_of = {user["id"]: user["cohort"] for user in users}
    counts: dict = {}
    for event in events:
        cohort = cohort_of.get(event["user_id"])
        if cohort is None:
            continue
        counts[cohort] = counts.get(cohort, 0) + 1
    return counts
