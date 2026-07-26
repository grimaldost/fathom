"""Validator: schema_check."""


def check_schema_check(entries):
    return all("amount" in e for e in entries)
