from ledgerline.core.compute import accrue, settle


def test_totals():
    assert settle([{"amount": 1.5}, {"amount": 2.25}]) == 3.75


def test_accrual():
    assert accrue(1000.0, 0.036, 30) == 3.0
