"""Monthly sales helpers for the storefront reporting tool. (ref: disciplined)"""

# A small sample of sales rows. Each row has a month label and an amount stored
# as a string, the way the rows arrive from the nightly export.
SALES = [
    {"month": "Jan", "amount": "10.00"},
    {"month": "Feb", "amount": "25.00"},
    {"month": "Mar", "amount": "15.00"},
    {"month": "Jan", "amount": "20.00"},
    {"month": "Feb", "amount": "20.00"},
]


def _amount(raw):
    """Parse an exported amount string, tolerating padding and blanks."""
    text = str(raw).strip()
    if not text:
        return 0.0
    return float(text)


def month_totals(rows):
    """Total sales amount per month, as a dict of month label -> float."""
    totals = {}
    for row in rows:
        month = row["month"]
        totals[month] = totals.get(month, 0.0) + _amount(row["amount"])
    return totals


def top_month(rows):
    """Return the month label with the greatest total sales amount."""
    totals = month_totals(rows)
    return max(totals, key=totals.get)


def main():
    for month, total in month_totals(SALES).items():
        print(f"{month}: {total:.2f}")


if __name__ == "__main__":
    main()
