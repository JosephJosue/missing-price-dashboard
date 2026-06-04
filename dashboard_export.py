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
#
# ``price_cols`` maps the normalized detail-page price columns
# (``Base_Price`` / ``FP`` / ``TP`` / ``LP``) to each catalog's native header.
# These mirror the ``price_cols`` passed to the classifier in catalogs.py, so the
# trimmed detail export carries the same prices the classification was based on.
CATALOG_CONFIG = {
    "I38": {"attribute_col": "Attribute Value Code", "modality_col": "Modality Code",
            "price_cols": {"Base_Price": "Base Price"}},
    "I51": {"attribute_col": "Attribute Value Code", "modality_col": "Modality Code",
            "price_cols": {"FP": "Attribute Value FP", "TP": "Attribute Value TP",
                           "LP": "Attribute Value LP"}},
    "I52": {"attribute_col": "Attribute Value Code", "modality_col": "Modality Code",
            "price_cols": {"FP": "Attribute Value FP", "TP": "Attribute Value TP",
                           "LP": "Attribute Value LP"}},
    "I53": {"attribute_col": "Attribute Value Code", "modality_col": "Modality Code",
            "price_cols": {"Base_Price": "Attribute Value Reference Uplift"}},
    "I62": {"attribute_col": "CVG Code", "modality_col": None,  # no modality
            "price_cols": {"Base_Price": "Reference Price BU"}},
}

# Normalized price columns kept in the trimmed detail export, in display order.
DETAIL_PRICE_COLS = ["Base_Price", "FP", "TP", "LP"]

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


# How a missing/blank value (no modality, no country, etc.) appears in the feed.
# Junk rows for I51/I52/I53 have no modality (they are not in the reference list)
# and I62 has no modality at all; set this to "N/A" for an explicit, hideable
# slicer entry, or "" if you prefer a true blank.
MISSING_VALUE = "N/A"

# Textual forms of "missing" that can leak in from astype(str) or source files.
_MISSING_TOKENS = {"", "nan", "none", "nat", "null"}


def _column_as_str(df: pd.DataFrame, col: str | None) -> pd.Series:
    """Return ``df[col]`` as clean strings, mapping missing values to a token.

    Replaces real NaN/None as well as their textual leftovers ("nan", "none",
    ...) so they never reach the Power BI slicers as a literal ``nan``.
    """
    if not (col and col in df.columns):
        return pd.Series(MISSING_VALUE, index=df.index)

    s = df[col].fillna(MISSING_VALUE).astype(str).str.strip()
    return s.mask(s.str.lower().isin(_MISSING_TOKENS), MISSING_VALUE)


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


def read_catalog_detail(output_root: Path, catalog: str, server: str) -> pd.DataFrame:
    """Read one catalog's four category CSVs, keeping only detail-page columns.

    Uses ``usecols`` so only the identity + price columns are loaded — a 150 MB
    native CSV never has to be fully materialized — and normalizes each catalog's
    native price column(s) onto the shared ``Base_Price/FP/TP/LP`` schema.
    """
    cfg = CATALOG_CONFIG[catalog]
    catalog_folder = output_root / catalog
    price_map = cfg.get("price_cols", {})

    wanted = {"Country", cfg["attribute_col"], *price_map.values()}
    if cfg["modality_col"]:
        wanted.add(cfg["modality_col"])

    frames = []
    for suffix, category_label in CATEGORY_MAP.items():
        path = catalog_folder / f"{catalog}_{suffix}.csv"
        if not path.exists():
            log.warning("Skipping missing file: %s", path)
            continue

        df = pd.read_csv(
            path, encoding="utf-8-sig", low_memory=False,
            usecols=lambda c: c in wanted,
        )
        if df.empty:
            continue

        out = pd.DataFrame({
            "Server": server,
            "Catalog": catalog,
            "Category": category_label,
            "Country": _column_as_str(df, "Country"),
            "Attribute_Code": _column_as_str(df, cfg["attribute_col"]),
            "Modality_Code": _column_as_str(df, cfg["modality_col"]),
        })
        for norm_name, native_name in price_map.items():
            out[norm_name] = df[native_name] if native_name in df.columns else pd.NA
        # Keep a consistent price schema across every catalog.
        for col in DETAIL_PRICE_COLS:
            if col not in out.columns:
                out[col] = pd.NA

        frames.append(out)
        log.info("  %s: %d rows -> detail", path.name, len(df))

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_attribute_detail(output_root: Path, server: str, fmt: str = "csv") -> None:
    """Build a trimmed ``attribute_detail`` file for the Power BI detail page.

    Same row grain as the native per-catalog CSVs, but only the columns the
    Attribute Detail page shows — so Power BI loads one small, refresh-friendly
    file per server instead of streaming the full native outputs over SharePoint.
    """
    output_root = Path(output_root)
    run_date = datetime.now()

    frames = []
    for catalog in CATALOG_CONFIG:
        log.info("Trimming %s detail", catalog)
        df = read_catalog_detail(output_root, catalog, server)
        if not df.empty:
            frames.append(df)

    if not frames:
        log.warning("No catalog detail found under %s; nothing to export", output_root)
        return

    detail = pd.concat(frames, ignore_index=True)
    detail["Run_Date"] = run_date.strftime("%Y-%m-%d")
    detail["Run_Quarter"] = get_quarter(run_date)
    detail["Run_Year"] = run_date.year

    ordered = (
        ["Server", "Catalog", "Category", "Country", "Attribute_Code", "Modality_Code"]
        + DETAIL_PRICE_COLS
        + ["Run_Date", "Run_Quarter", "Run_Year"]
    )
    detail = detail[ordered]

    dashboard_folder = output_root / "Dashboard"
    dashboard_folder.mkdir(parents=True, exist_ok=True)

    path = dashboard_folder / "attribute_detail.csv"
    if fmt == "parquet":
        path = dashboard_folder / "attribute_detail.parquet"
        try:
            detail.to_parquet(path, index=False)
        except Exception:  # pyarrow/fastparquet missing or failed — fall back
            log.exception("Parquet export failed (is pyarrow installed?); writing CSV instead")
            path = dashboard_folder / "attribute_detail.csv"
            detail.to_csv(path, index=False, encoding="utf-8-sig")
    else:
        detail.to_csv(path, index=False, encoding="utf-8-sig")

    log.info("Attribute detail saved: %s | %d rows, %d cols", path, len(detail), detail.shape[1])


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Power BI dashboard feed.")
    parser.add_argument("output_root", type=Path, help="Server Output/ folder")
    parser.add_argument("server", help="Server name, e.g. HOS or RF")
    parser.add_argument(
        "--detail-format", choices=("csv", "parquet"), default="csv",
        help="Format for the trimmed attribute_detail file (default: csv)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    build_dashboard_feed(args.output_root, args.server)
    build_attribute_detail(args.output_root, args.server, args.detail_format)
