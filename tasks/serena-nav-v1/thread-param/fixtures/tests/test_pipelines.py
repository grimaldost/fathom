from ledgerline.legacy import oldapi
from ledgerline.pipelines.daily import run_daily
from ledgerline.pipelines.monthly import run_monthly


def test_daily():
    assert run_daily([{"amount": 5.0}], 2.0) == 10.0


def test_monthly():
    assert run_monthly([[{"amount": 1.0}], [{"amount": 2.0}]], 1.0) == 3.0


def test_legacy_surface():
    assert oldapi.legacy_total([{"amount": 4.0}]) == 4.0
