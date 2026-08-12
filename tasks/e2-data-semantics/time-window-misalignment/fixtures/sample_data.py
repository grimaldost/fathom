"""A small March 2026 sample, kept beside the transform for local runs."""

ORDERS = [
    {
        "order_id": "W1",
        "event_ts": "2026-02-28T23:30:00+00:00",
        "load_date": "2026-03-01",
        "amount_local": "100.00",
        "currency": "EUR",
    },
    {
        "order_id": "W2",
        "event_ts": "2026-03-01T10:00:00+00:00",
        "load_date": "2026-03-01",
        "amount_local": "200.00",
        "currency": "EUR",
    },
    {
        "order_id": "W3",
        "event_ts": "2026-03-15T12:00:00+00:00",
        "load_date": "2026-03-15",
        "amount_local": "300.00",
        "currency": "EUR",
    },
    {
        "order_id": "W4",
        "event_ts": "2026-03-31T22:00:00+00:00",
        "load_date": "2026-04-01",
        "amount_local": "400.00",
        "currency": "EUR",
    },
    {
        "order_id": "W5",
        "event_ts": "2026-03-20T01:00:00+00:00",
        "load_date": "2026-03-19",
        "amount_local": "500.00",
        "currency": "EUR",
    },
]

FX_RATES = [
    {"rate_date": "2026-02-28", "currency": "EUR", "rate": "1.05"},
    {"rate_date": "2026-03-01", "currency": "EUR", "rate": "1.10"},
    {"rate_date": "2026-03-15", "currency": "EUR", "rate": "1.20"},
    {"rate_date": "2026-03-19", "currency": "EUR", "rate": "1.30"},
    {"rate_date": "2026-03-20", "currency": "EUR", "rate": "1.40"},
    {"rate_date": "2026-03-31", "currency": "EUR", "rate": "1.50"},
    {"rate_date": "2026-04-01", "currency": "EUR", "rate": "1.60"},
]
