"""Validator: limits_check."""


def check_limits_check(entries):
    return all("amount" in e for e in entries)
