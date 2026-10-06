"""Keep the suite independent of the FATHOM_HOME of whoever runs it.

FATHOM_HOME names the data root every fathom command runs against, and it wins over the
working directory. A developer who sets it for their own data would otherwise have every
test that runs a fathom command (in process or as a subprocess, which inherits the
environment) point at that data root instead of the temporary one the test built, and a
test that writes would write there. Tests that need the variable set it themselves.

Stdlib only; pytest imports this file before it collects any test. The test files that
run a fathom command also clear the variable themselves, for bare ``python tests/...``
runs.
"""

from __future__ import annotations

import os

os.environ.pop("FATHOM_HOME", None)
