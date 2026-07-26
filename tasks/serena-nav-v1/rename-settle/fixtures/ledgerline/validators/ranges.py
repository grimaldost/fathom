"""Validator: ranges."""


def check_ranges(entries):
    return all("amount" in e for e in entries)
