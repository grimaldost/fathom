"""Enable ``python -m fathom`` — a shim-free entry point.

Complements the ``fathom`` console script for environments where the generated
``.exe`` shim cannot run (e.g. it is blocked by a Windows Application Control /
Smart App Control policy — os error 4551). Same entry as the console script,
``fathom.cli:main``, so ``python -m fathom report <bank>`` behaves identically to
``fathom report <bank>``.
"""

import sys

from fathom.cli import main

if __name__ == "__main__":
    sys.exit(main())
