from reconciler.pipelines.daily import run_daily


def test_daily_runs():
    assert run_daily([{"amount": 10.0}], 0.1) >= 0
