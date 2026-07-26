from ledgerline.adapters.csv_io import load_and_settle
from ledgerline.adapters.report import build_report


def test_csv():
    assert load_and_settle(["1.10", "2.20"]) == 3.30


def test_report():
    r = build_report([{"amount": 10.0}], 1.1)
    assert r == {"total": 10.0, "converted": 11.0}
