"""
CLI entry when ``agentos.exe`` is not on PATH::

    python -m agentos run workflows/sample.yaml
    python -m agentos diagnose <run_id>
"""

from __future__ import annotations

import sys


if __name__ == "__main__":
    from main import main as cli_main

    sys.exit(cli_main())
