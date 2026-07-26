from reconciler.core.engine import reconcile


def test_reconcile():
    assert reconcile([{"amount": 1.5}, {"amount": 2.25}]) == 3.75
