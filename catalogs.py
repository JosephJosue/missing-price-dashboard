"""Per-catalog pricing-coverage analyses (I38, I51, I52, I53, I62).

Each ``run_iXX`` function loads its source spreadsheets for a given server,
classifies attribute pricing into priced / not-priced / zero / junk buckets and
writes the result CSVs. They all share the engine in :mod:`common`, so the
classification logic lives in exactly one place.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

from common import (
    ATTRIBUTE_COL,
    classify,
    classify_by_price,
    export_csv,
    export_results,
    find_junk,
    load_excel,
)

log = logging.getLogger(__name__)

# Price columns used by the "FP/TP/LP" catalogs (I51, I52).
FPLP_COLS = ("Attribute Value FP", "Attribute Value TP", "Attribute Value LP")


def _input_name(stem: str, server: str) -> str:
    """Build a source spreadsheet name, e.g. ``I35_...._HOS_PROD.xlsx``."""
    return f"{stem}_{server}_PROD.xlsx"


def _b53_codes(b53: pd.DataFrame, *, use_modality_base_price: bool):
    """Attribute codes from B53 filtered by the 'Use Modality Base Price' flag."""
    flag = b53.iloc[:, [2, 21]].copy()
    flag.columns = [ATTRIBUTE_COL, "Use Modality Base Price"]
    flag = flag[flag["Use Modality Base Price"] == use_modality_base_price]
    return flag[ATTRIBUTE_COL].dropna().unique()


# ---------------------------------------------------------------------------
# I38 — Modality Base Price vs master attribute list
# ---------------------------------------------------------------------------

def run_i38(server, i_dir, b_dir, output, country=None, modality=None):
    log.info("Running I38 analysis")
    i35 = load_excel(i_dir, _input_name("I35_MSAttributeValueLevel_1", server))
    i38 = load_excel(i_dir, _input_name("I38_ModalityBasePrice_1", server))
    b53 = load_excel(b_dir, _input_name("B53_MaintenanceServiceAttributeValue_1", server))

    valid = _b53_codes(b53, use_modality_base_price=True)
    i35 = i35[i35[ATTRIBUTE_COL].isin(valid)]
    log.info("I35 after filtering valid codes: %d rows", len(i35))

    key_cols = ["Country", ATTRIBUTE_COL, "Modality Code"]
    results = classify(i35, i38, key_cols, ["Base Price"])

    export_results(results, output / "I38", "I38", country=country, modality=modality)
    log.info("I38 completed")


# ---------------------------------------------------------------------------
# I51 — Optional Service attribute values vs I37
# ---------------------------------------------------------------------------

def run_i51(server, i_dir, b_dir, output, country=None, modality=None):
    log.info("Running I51 analysis")
    i37 = load_excel(i_dir, _input_name("I37_OSAttributeValueLevel_1", server))
    i51 = load_excel(i_dir, _input_name("I51_OptionalServiceAttributeValue_1", server))

    key_cols = ["Country", ATTRIBUTE_COL]
    results = classify(
        i37, i51, key_cols, FPLP_COLS, ref_extra_cols=["Modality Code"]
    )

    export_results(results, output / "I51", "I51", country=country, modality=modality)
    log.info("I51 completed")


# ---------------------------------------------------------------------------
# I52 — Strategic Part attribute values vs I36 (+ B52 cross-check)
# ---------------------------------------------------------------------------

def run_i52(server, i_dir, b_dir, output, country=None, modality=None):
    log.info("Running I52 analysis")
    i36 = load_excel(i_dir, _input_name("I36_SPAttributeValueLevel_1", server))
    i52 = load_excel(i_dir, _input_name("I52_StrategicPartAttributeValue_1", server))
    b52 = load_excel(b_dir, _input_name("B52_StrategicPartAttributeValue_1", server))

    key_cols = ["Country", ATTRIBUTE_COL]
    priced, not_priced, zero, junk = classify(
        i36, i52, key_cols, FPLP_COLS, ref_extra_cols=["Modality Code"]
    )

    # Flag priced rows that are missing from the B52 reference list.
    b52_codes = b52[ATTRIBUTE_COL].dropna().unique()
    priced = priced.copy()
    priced["Available_in_B52"] = priced[ATTRIBUTE_COL].isin(b52_codes)
    missing_in_b52 = priced[~priced["Available_in_B52"]]

    export_results(
        (priced, not_priced, zero, junk),
        output / "I52", "I52", country=country, modality=modality,
    )
    export_csv(missing_in_b52, output / "I52", "I52_missing_in_B52")
    log.info("I52 completed")


# ---------------------------------------------------------------------------
# I53 — Maintenance Service attribute values vs I35
# ---------------------------------------------------------------------------

def run_i53(server, i_dir, b_dir, output, country=None, modality=None):
    log.info("Running I53 analysis")
    i35 = load_excel(i_dir, _input_name("I35_MSAttributeValueLevel_1", server))
    i53 = load_excel(i_dir, _input_name("I53_MaintenanceServiceAttributeValue_1", server))
    b53 = load_excel(b_dir, _input_name("B53_MaintenanceServiceAttributeValue_1", server))

    valid = _b53_codes(b53, use_modality_base_price=False)
    i35 = i35[i35[ATTRIBUTE_COL].isin(valid)]

    key_cols = ["Country", ATTRIBUTE_COL]
    results = classify(
        i35, i53, key_cols,
        ["Attribute Value Reference Uplift"],
        ref_extra_cols=["Modality Code"],
    )

    export_results(results, output / "I53", "I53", country=country, modality=modality)
    log.info("I53 completed")


# ---------------------------------------------------------------------------
# I62 — Commercial System pricing (multi-table join)
# ---------------------------------------------------------------------------

def run_i62(server, i_dir, b_dir, output, country=None, modality=None):
    log.info("Running I62 analysis")
    i62 = load_excel(i_dir, _input_name("I62_CommercialSystem_1", server))
    b49 = load_excel(b_dir, _input_name("B49_CommercialSystem_1", server))
    i32 = load_excel(i_dir, _input_name("I32_CommercialViewGroupLocal_1", server))
    b32 = load_excel(b_dir, _input_name("B32_System_1", server))

    i32 = i32.rename(columns={"CVGCode": "CVG Code"})

    matched = i62.merge(
        b49[["CVG Code", "Initial CSP", "Core Option"]], on="CVG Code", how="right"
    )
    matched = matched.merge(
        i32[["Country", "CVG Code", "CVGType", "Used In Country YN"]],
        on=["CVG Code", "Country"], how="left",
    )
    matched = matched.merge(
        b32[[
            "System Code", "System Inactive", "System End Of Production",
            "System End Of Life", "System End Of Service",
        ]],
        left_on="Initial CSP", right_on="System Code", how="left",
    )

    priced, not_priced, zero = classify_by_price(
        matched, ["Reference Price BU"], exclude_ex=False
    )
    junk = find_junk(i62, b49[["CVG Code"]], ["CVG Code"])

    export_results(
        (priced, not_priced, zero, junk),
        output / "I62", "I62", country=country, modality=modality,
    )
    log.info("I62 completed")


# All catalog runners, in execution order.
CATALOG_RUNNERS: tuple = (run_i38, run_i51, run_i52, run_i53, run_i62)


def run_all(
    server: str,
    i_dir: Path,
    b_dir: Path,
    output: Path,
    country: Iterable[str] | None = None,
    modality: Iterable[str] | None = None,
) -> None:
    """Run every catalog analysis for ``server``, isolating per-catalog errors."""
    for runner in CATALOG_RUNNERS:
        try:
            runner(server, i_dir, b_dir, output, country, modality)
        except Exception:  # keep going so one bad catalog doesn't stop the rest
            log.exception("Catalog %s failed", runner.__name__)
