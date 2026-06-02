"""Central configuration for the pricing-coverage pipeline.

BASE_DIR points to the folder that contains the HOS/ and RF/ subfolders.
Override it by setting the PRICING_BASE_DIR environment variable, or just
edit the default path below to match your machine.

The expected on-disk layout per server is::

    <BASE_DIR>/<SERVER>/
        I files/      input I-catalog spreadsheets
        B files/      input B-reference spreadsheets
        Output/       generated CSVs (created automatically)
"""

from __future__ import annotations

import os
from pathlib import Path

# Servers the pipeline knows how to process.
SERVERS = ("HOS", "RF")

# Edit the path below if you are not using the PRICING_BASE_DIR env var.
_DEFAULT = r"C:\Users\320270203\OneDrive - Philips\PST Activities - No & Zero Pricing\BI Connector"

BASE_DIR = Path(os.environ.get("PRICING_BASE_DIR", _DEFAULT))


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
