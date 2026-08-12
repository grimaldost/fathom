"""Proration arithmetic for mid-cycle subscription changes.

Every function here is meant to implement the rule of the same name in RULES.md.
"""


def days_in_cycle(start_day: int, end_day: int) -> int:
    """P1: the cycle length, counting the start day and not the end day."""
    return end_day - start_day


def unused_days(change_day: int, end_day: int) -> int:
    """P2: whole days left after the change, counting the change day itself."""
    return end_day - change_day


def credit(amount_cents: int, unused: int, cycle: int) -> int:
    """P3: the credit for the unused part of the old plan, rounded HALF UP."""
    if cycle <= 0:
        return 0
    return int(amount_cents * unused / cycle)


def charge(amount_cents: int, unused: int, cycle: int) -> int:
    """P4: the charge for the unused part of the new plan, rounded HALF UP."""
    if cycle <= 0:
        return 0
    scaled = amount_cents * unused
    whole, remainder = divmod(scaled, cycle)
    return whole + (1 if remainder * 2 >= cycle else 0)


def net(old_cents: int, new_cents: int, change_day: int, start_day: int, end_day: int) -> int:
    """P5: what the customer is billed now: the new charge less the old credit."""
    cycle = days_in_cycle(start_day, end_day)
    unused = unused_days(change_day, end_day)
    return charge(new_cents, unused, cycle) - credit(old_cents, unused, cycle)


def is_refund(net_cents: int) -> bool:
    """P6: a negative net is a refund, and exactly zero is not."""
    return net_cents < 0
