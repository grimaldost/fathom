from reconciler.accounts.api import run as run_l1
from reconciler.custody.mapper import run as run_l2
from reconciler.limits.policies import run as run_l3


def test_chain():
    entries = [{"amount": 2.0}]
    assert run_l1(entries) == 2.0
    assert run_l2(entries) == 2.0
    assert run_l3(entries) == 2.0
