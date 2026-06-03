"""Post-processor that consolidates per-catalog CSVs for Power BI.

Reads the four category CSVs produced for each catalog and writes two files
into ``<output_root>/Dashboard``:

* ``dashboard_feed.csv`` — flat table powering all visuals (overwritten each run)
* ``run_history.csv``    — per-run category counts (appended each run)

The original per-catalog CSVs are left untouched so Power BI download buttons
can keep linking to them with their native columns.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

# Per-catalog source columns normalized to the common dashboard schema.
CATALOG_CONFIG = {
    "I38": {"attribute_col": "Attribute Value Code", "modality_col": "Modality Code"},
    "I51": {"attribute_col": "Attribute Value Code", "modality_col": "Modality Code"},
    "I52": {"attribute_col": "Attribute Value Code", "modality_col": "Modality Code"},
    "I53": {"attribute_col": "Attribute Value Code", "modality_col": "Modality Code"},
    "I62": {"attribute_col": "CVG Code", "modality_col": None},  # no modality
}

# Maps the CSV file suffix to its human-readable category label.
CATEGORY_MAP = {
    "priced": "Priced",
    "not_priced": "Not Priced",
    "zero_priced": "Price in 0",
    "junk_price": "Junk Price",
}

HISTORY_KEYS = ["Server", "Run_Date", "Run_Quarter", "Run_Year", "Catalog", "Category"]


def get_quarter(dt: datetime) -> str:
    """Return a quarter label such as ``'Q2'`` for the given date."""
    return f"Q{(dt.month - 1) // 3 + 1}"


def _column_as_str(df: pd.DataFrame, col: str | None) -> pd.Series:
    """Return ``df[col]`` as strings, or an empty column if it's absent."""
    if col and col in df.columns:
        return df[col].astype(str)
    return pd.Series("", index=df.index)


def read_catalog_outputs(output_root: Path, catalog: str, server: str) -> pd.DataFrame:
    """Read one catalog's four category CSVs into a normalized DataFrame."""
    cfg = CATALOG_CONFIG[catalog]
    catalog_folder = output_root / catalog

    frames = []
    for suffix, category_label in CATEGORY_MAP.items():
        path = catalog_folder / f"{catalog}_{suffix}.csv"
        if not path.exists():
            log.warning("Skipping missing file: %s", path)
            continue

        df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        if df.empty:
            continue

        frames.append(pd.DataFrame({
            "Server": server,
            "Catalog": catalog,
            "Category": category_label,
            "Country": _column_as_str(df, "Country"),
            "Attribute_Code": _column_as_str(df, cfg["attribute_col"]),
            "Modality_Code": _column_as_str(df, cfg["modality_col"]),
        }))
        log.info("  %s: %d rows -> %s", path.name, len(df), category_label)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_dashboard_feed(output_root: Path, server: str) -> None:
    """Build ``dashboard_feed.csv`` and append to ``run_history.csv``."""
    output_root = Path(output_root)
    run_date = datetime.now()

    frames = []
    for catalog in CATALOG_CONFIG:
        log.info("Processing %s", catalog)
        df = read_catalog_outputs(output_root, catalog, server)
        if not df.empty:
            frames.append(df)

    if not frames:
        log.warning("No data found under %s; nothing to export", output_root)
        return

    feed = pd.concat(frames, ignore_index=True)
    feed["Run_Date"] = run_date.strftime("%Y-%m-%d")
    feed["Run_Quarter"] = get_quarter(run_date)
    feed["Run_Year"] = run_date.year

    dashboard_folder = output_root / "Dashboard"
    dashboard_folder.mkdir(parents=True, exist_ok=True)

    feed_path = dashboard_folder / "dashboard_feed.csv"
    feed.to_csv(feed_path, index=False, encoding="utf-8-sig")
    log.info("Dashboard feed saved: %s | %d rows", feed_path, len(feed))

    summary = feed.groupby(HISTORY_KEYS).size().reset_index(name="Count")
    history_path = dashboard_folder / "run_history.csv"
    is_new = not history_path.exists()
    summary.to_csv(
        history_path, mode="w" if is_new else "a",
        index=False, header=is_new, encoding="utf-8-sig",
    )
    log.info("Run history %s: %s", "created" if is_new else "appended", history_path)

    _log_summary(feed, server, run_date)


def _log_summary(feed: pd.DataFrame, server: str, run_date: datetime) -> None:
    counts = feed.groupby("Category").size()
    total = int(counts.sum())
    log.info("=== Dashboard export summary (%s, %s) ===",
             server, run_date.strftime("%Y-%m-%d %H:%M"))
    for cat in CATEGORY_MAP.values():
        count = int(counts.get(cat, 0))
        pct = (count / total * 100) if total else 0
        log.info("  %-14s %8d (%5.1f%%)", cat, count, pct)
    log.info("  %-14s %8d", "TOTAL", total)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Power BI dashboard feed.")
    parser.add_argument("output_root", type=Path, help="Server Output/ folder")
    parser.add_argument("server", help="Server name, e.g. HOS or RF")
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    build_dashboard_feed(args.output_root, args.server)
