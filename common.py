"""Reusable building blocks shared by every catalog analysis.

These are plain module-level functions (no classes): I/O helpers plus a small,
generic price-classification engine that all I-catalog scripts compose from.
"""

from __future__ import annotations

import functools
import logging
import operator
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

log = logging.getLogger(__name__)

ATTRIBUTE_COL = "Attribute Value Code"

# Standard output suffixes, in the order the analysis functions return them.
RESULT_SUFFIXES = ("priced", "not_priced", "zero_priced", "junk_price")


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_excel(folder: Path, filename: str) -> pd.DataFrame:
    """Read an Excel file and strip whitespace from its column headers."""
    df = pd.read_excel(Path(folder) / filename)
    df.columns = df.columns.str.strip()
    log.info("Loaded %s | rows: %d", filename, len(df))
    return df


def export_csv(df: pd.DataFrame, folder: Path, name: str) -> Path:
    """Write ``df`` to ``<folder>/<name>.csv`` (UTF-8 BOM for Excel/Power BI)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info("Saved %s | rows: %d", path.name, len(df))
    return path


def apply_filters(
    df: pd.DataFrame,
    country: Iterable[str] | None = None,
    modality: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Optionally filter rows by country and/or modality code."""
    if country and "Country" in df.columns:
        df = df[df["Country"].isin(country)]
    if modality and "Modality Code" in df.columns:
        df = df[df["Modality Code"].isin(modality)]
    return df


# ---------------------------------------------------------------------------
# Classification engine
# ---------------------------------------------------------------------------

def _exclude_ex_mask(df: pd.DataFrame, attr_col: str) -> pd.Series:
    """Mask dropping attribute codes ending in ``_ex`` (case-insensitive)."""
    if attr_col not in df.columns:
        return pd.Series(True, index=df.index)
    return ~df[attr_col].astype(str).str.lower().str.endswith("_ex", na=False)


def _combine(masks: Iterable[pd.Series]) -> pd.Series:
    """Logical AND of several boolean masks."""
    return functools.reduce(operator.and_, masks)


def classify_by_price(
    matched: pd.DataFrame,
    price_cols: Sequence[str],
    *,
    attr_col: str = ATTRIBUTE_COL,
    exclude_ex: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split ``matched`` into (priced, not_priced, zero_priced).

    A row is *priced* when every column in ``price_cols`` is present and
    non-zero, *not_priced* when they are all null, and *zero_priced* when they
    are all zero. ``_ex`` attribute codes are dropped from the latter two
    buckets when ``exclude_ex`` is set.
    """
    priced_mask = _combine(matched[c].notna() & (matched[c] != 0) for c in price_cols)
    not_priced_mask = _combine(matched[c].isna() for c in price_cols)
    zero_mask = _combine(matched[c] == 0 for c in price_cols)

    priced = matched[priced_mask].drop_duplicates()
    not_priced = matched[not_priced_mask]
    zero = matched[zero_mask]

    if exclude_ex:
        not_priced = not_priced[_exclude_ex_mask(not_priced, attr_col)]
        zero = zero[_exclude_ex_mask(zero, attr_col)]

    return priced, not_priced.drop_duplicates(), zero.drop_duplicates()


def find_junk(
    pricing: pd.DataFrame,
    reference: pd.DataFrame,
    key_cols: Sequence[str],
) -> pd.DataFrame:
    """Pricing rows that have no matching key in the reference table."""
    merged = pricing.merge(reference, on=list(key_cols), how="left", indicator=True)
    return (
        merged[merged["_merge"] == "left_only"]
        .drop(columns="_merge")
        .drop_duplicates()
    )


def classify(
    reference: pd.DataFrame,
    pricing: pd.DataFrame,
    key_cols: Sequence[str],
    price_cols: Sequence[str],
    *,
    ref_extra_cols: Sequence[str] = (),
    exclude_ex: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the standard four-way analysis for one catalog.

    The reference table (e.g. the master attribute list) is right-joined onto
    the pricing table on ``key_cols``; ``ref_extra_cols`` are pulled across so
    the output keeps useful reference columns. Returns
    (priced, not_priced, zero_priced, junk).
    """
    key_cols = list(key_cols)
    ref = reference[key_cols + list(ref_extra_cols)]

    matched = pricing.merge(ref, on=key_cols, how="right")
    priced, not_priced, zero = classify_by_price(
        matched, price_cols, exclude_ex=exclude_ex
    )
    junk = find_junk(pricing, ref, key_cols)
    return priced, not_priced, zero, junk


def export_results(
    results: Sequence[pd.DataFrame],
    output_folder: Path,
    prefix: str,
    *,
    suffixes: Sequence[str] = RESULT_SUFFIXES,
    country: Iterable[str] | None = None,
    modality: Iterable[str] | None = None,
) -> None:
    """Filter each result frame and write it as ``<prefix>_<suffix>.csv``."""
    for df, suffix in zip(results, suffixes):
        df = apply_filters(df, country, modality)
        export_csv(df, output_folder, f"{prefix}_{suffix}")
