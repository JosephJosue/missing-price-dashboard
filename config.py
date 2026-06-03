"""Central configuration for the pricing-coverage pipeline.

All paths are resolved from the ``PRICING_BASE_DIR`` environment variable so
the code never embeds a user- or machine-specific location. Set it once::

    # Windows (PowerShell)
    setx PRICING_BASE_DIR "C:\\Users\\<you>\\Philips\\PST Activities - No & Zero Pricing"

    # macOS / Linux
    export PRICING_BASE_DIR="$HOME/PST Activities - No & Zero Pricing"

The expected on-disk layout per server is::

    <PRICING_BASE_DIR>/<SERVER>/
        I files/      input I-catalog spreadsheets
        B files/      input B-reference spreadsheets
        Output/       generated CSVs (created automatically)
"""

from __future__ import annotations

import os
from pathlib import Path

# Servers the pipeline knows how to process.
SERVERS = ("HOS", "RF")

# Base directory holding one sub-folder per server. Defaults to a folder in the
# user's home directory so the project runs out-of-the-box without editing code.
BASE_DIR = Path(
    os.environ.get(
        "PRICING_BASE_DIR",
        Path.home() / "PST Activities - No & Zero Pricing",
    )
).expanduser()


def server_paths(server: str) -> dict[str, Path]:
    """Return the input/output folders for ``server`` (e.g. ``"HOS"``)."""
    if server not in SERVERS:
        raise ValueError(f"Unknown server {server!r}; expected one of {SERVERS}")

    root = BASE_DIR / server
    return {
        "i_files": root / "I files",
        "b_files": root / "B files",
        "output": root / "Output",
    }
