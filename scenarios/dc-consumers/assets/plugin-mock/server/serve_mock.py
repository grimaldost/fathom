"""Stdio launcher for the data-context MCP server over a frozen corpus snapshot.

Eval-harness artifact (fathom bank ``dc-granularity-v1``, FINE arm) — not part
of the data-context product surface. Serves the product's full twelve-tool
discovery/actuation facade exactly as ``data_context.server.create_server``
builds it. ``argv[1]`` = corpus directory (the plugin-local frozen snapshot).
"""

import sys
from pathlib import Path

from data_context.backend.local import LocalCorpusBackend
from data_context.provenance import CorpusManifest, load_verified
from data_context.server import create_server


def main() -> None:
    corpus_dir = Path(sys.argv[1])
    server = create_server(
        LocalCorpusBackend(load_verified(corpus_dir)),
        CorpusManifest.load(corpus_dir),
    )
    server.run()


if __name__ == "__main__":
    main()
