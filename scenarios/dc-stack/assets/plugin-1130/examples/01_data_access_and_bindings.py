"""Data access: doctor-first, fail-closed reads, and what to do when a read fails.

Scenario
--------
You install treasuryutils (internally, via Karavela) and read a dataset. The canonical
DataTools datasets default to Stone sources -- BigQuery, Databricks, REST -- which, as an
internal Stone user, you reach **with your own credentials**. A read can still fail
fail-closed when auth, source bindings, or data files are not yet wired. This example
shows the right first move: inspect bindings with the structured doctor, read fail-closed
with ``covers=``, and follow the error's recovery routing instead of papering over it.

What this demonstrates
----------------------
- ``config_status()`` -- the machine-readable doctor: which datasets are bound, which are
  proprietary-driver primitives, and which referenced auth profiles are unconfigured.
- The fail-closed read pattern ``DatasetClient(name).get(covers=(lo, hi))``.
- Catching a fail-closed error (``SourceExtractionError`` / ``PipelineExecutionError`` /
  ``CoverageError``) and acting on its recovery routing -- never continuing with
  silently-stale or missing data.

Dual-mode
---------
With credentials configured this reads the live ``cdi_daily`` (BigQuery via the
``gcp-identity`` profile). Set ``TU_EXAMPLES_OFFLINE=1`` to skip the live read and just
show the doctor + the pattern (deterministic, no credentials) -- the smoke test does this.

treasuryutils APIs
------------------
- ``treasuryutils.datatools.config_status`` -> ``ConfigStatusReport`` / ``DatasetStatus``
- ``treasuryutils.datatools.DatasetClient`` -> ``.get(covers=...)``
- ``treasuryutils.datatools`` error classes: ``SourceExtractionError``,
  ``PipelineExecutionError`` (the first-read failure classes; ``CoverageError`` is the
  separate bound-but-stale case)

Why treasuryutils, not hand-rolled
----------------------------------
The failure modes here are the whole point: a read that "works" by serving stale cache,
or one that silently returns fewer rows than asked, is worse than a loud error.
``covers=`` makes staleness raise ``CoverageError`` instead of lying, and ``config_status``
lets you see the binding state before you read. Do not wrap these in ``except: pass``.
See ``references/datatools_api.md`` and the ``setup-source-bindings`` skill.

Install
-------
``treasuryutils[datatools]``

Run
---
``python examples/01_data_access_and_bindings.py``            (live read with credentials)
``TU_EXAMPLES_OFFLINE=1 python examples/01_data_access_and_bindings.py``   (doctor only)

Expected output (doctor is always printed; the live read section varies by environment)
---------------------------------------------------------------------------------------
    === DataTools: doctor-first data access ===

    Catalog: 24 datasets, serve_mode = 'cache'
    Bindings: 0 of 24 datasets have an explicit source binding.

    Proprietary-driver primitives (need credentials or a binding before first read):
      cdi_daily          source=bigquery
      di_curve           source=bigquery
      market_fixings     source=bigquery
"""

from __future__ import annotations

from datetime import date

from _support import EXAMPLES_OFFLINE

from treasuryutils.datatools import (
    DatasetClient,
    PipelineExecutionError,
    SourceExtractionError,
    config_status,
)

DATASET = 'cdi_daily'
COVERS = (date(2024, 1, 1), date(2024, 1, 31))


def main() -> None:
    print('=== DataTools: doctor-first data access ===\n')

    # 1. Inspect the binding configuration BEFORE reading (the structured doctor).
    report = config_status()
    bound = sum(1 for d in report.datasets if d.has_binding)
    print(f'Catalog: {len(report.datasets)} datasets, serve_mode = {report.serve_mode!r}')
    print(
        f'Bindings: {bound} of {len(report.datasets)} datasets have an explicit source binding.\n'
    )

    proprietary = [d for d in report.datasets if d.proprietary_driver]
    print('Proprietary-driver primitives (need credentials or a binding before first read):')
    for status in proprietary:
        print(f'  {status.dataset_name:<18} source={status.source_type}')

    # 2. The fail-closed read pattern.
    lo, hi = COVERS
    print('\nFail-closed read pattern:')
    print(
        f'  df = DatasetClient({DATASET!r}).get('
        f'covers=(date({lo.year}, {lo.month}, {lo.day}), date({hi.year}, {hi.month}, {hi.day})))'
    )

    if EXAMPLES_OFFLINE:
        print('\n[offline] TU_EXAMPLES_OFFLINE set -> not attempting the live read.')
        print(
            f'  With credentials, this reads {DATASET!r} (BigQuery via the gcp-identity profile).'
        )
        return

    # 3. Attempt the live read. With reachable credentials it returns data; otherwise it
    #    raises a fail-closed error and we surface the recovery routing rather than swallow it.
    print(f'\nAttempting the live read of {DATASET!r} ...')
    try:
        frame = DatasetClient(DATASET).get(covers=COVERS)
    except (SourceExtractionError, PipelineExecutionError) as exc:
        print(
            f'  -> raised {type(exc).__name__} -- a fail-closed signal, not silently-stale data.\n'
        )
        print('Recovery (do this, do NOT except-and-continue):')
        print('  1. Doctor: `python -m treasuryutils.datatools doctor` (binding + auth state).')
        print(
            f'  2. Verify your access to the default source -- {DATASET!r} (BigQuery) uses the '
            "'gcp-identity' auth profile; configure it with the auth-setup skill."
        )
        print(
            f'  3. Rebind {DATASET!r} ONLY if you intend a non-default source '
            '(setup-source-bindings skill).'
        )
        print(
            '  4. Re-read with covers=(lo, hi) so staleness raises CoverageError, not wrong data.'
        )
    else:
        print(f'  -> read OK: {frame.height} rows, columns {frame.columns}')
        print(f'     (this environment reaches {DATASET!r} with valid credentials.)')


if __name__ == '__main__':
    main()
