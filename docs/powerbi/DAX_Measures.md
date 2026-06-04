# Pricing Coverage Dashboard — DAX Measures & Conditional Formatting (Real Data)

Companion to `PowerBI_Build_Guide.md`. These measures target the **real pipeline model**:

- **`DashboardFeed`** — one row per attribute (snapshot). Columns: `Server, Catalog, Category, Country,
  Attribute_Code, Modality_Code, Run_Date, Run_Quarter, Run_Year`. → Overview aggregates.
- **`RunHistory`** — pre-aggregated counts (appended each run). Columns: `Server, Run_Date, Run_Quarter,
  Run_Year, Catalog, Category, Count`. → Trend + real deltas.
- **`AttributeDetail`** — the trimmed `attribute_detail.csv`: `Server, Catalog, Category, Country,
  Attribute_Code, Modality_Code, Base_Price, FP, TP, LP, Run_*`. → Detail page.
- Dims: `DimCategory[Category, SortOrder, Color]`, `DimServer/Country/Catalog/Modality`.

Put all measures on a dedicated **`_Measures`** table.

> Key change vs the mock model: counts are **`COUNTROWS`** over the long feed (no `SUM` of pivoted
> columns), and quarter deltas are computed from the **real `RunHistory`** instead of hardcoded numbers.

---

## 1. Base counts (Overview — from `DashboardFeed`)

```DAX
Total Attrs  = COUNTROWS ( DashboardFeed )

Priced       = CALCULATE ( [Total Attrs], DashboardFeed[Category] = "Priced" )
Not Priced   = CALCULATE ( [Total Attrs], DashboardFeed[Category] = "Not Priced" )
Zero Priced  = CALCULATE ( [Total Attrs], DashboardFeed[Category] = "Price in 0" )
Junk Price   = CALCULATE ( [Total Attrs], DashboardFeed[Category] = "Junk Price" )
```

> If you put `Category` on a visual's legend/axis (donut, stacked column), just use `[Total Attrs]` — the
> visual slices it by category for you. The four explicit measures above are for the KPI cards and the
> summary table where each category is its own column.

---

## 2. Coverage & share measures

```DAX
Coverage % = DIVIDE ( [Priced], [Total Attrs] )

-- Within-row shares for the heat matrix (share of the current Country row)
Priced %      = DIVIDE ( [Priced],      [Total Attrs] )
Not Priced %  = DIVIDE ( [Not Priced],  [Total Attrs] )
Zero Priced % = DIVIDE ( [Zero Priced], [Total Attrs] )
Junk %        = DIVIDE ( [Junk Price],  [Total Attrs] )

-- "% of grand total" for KPI card footers (ignores the category filter, keeps slicers)
Category % of Total =
    DIVIDE ( [Total Attrs], CALCULATE ( [Total Attrs], REMOVEFILTERS ( DimCategory ) ) )
```

Per-card footer percentages (one per KPI card):

```DAX
Priced % of Total     = DIVIDE ( [Priced],      CALCULATE ( [Total Attrs], REMOVEFILTERS ( DimCategory ) ) )
Not Priced % of Total = DIVIDE ( [Not Priced],  CALCULATE ( [Total Attrs], REMOVEFILTERS ( DimCategory ) ) )
Zero % of Total       = DIVIDE ( [Zero Priced], CALCULATE ( [Total Attrs], REMOVEFILTERS ( DimCategory ) ) )
Junk % of Total       = DIVIDE ( [Junk Price],  CALCULATE ( [Total Attrs], REMOVEFILTERS ( DimCategory ) ) )
```

---

## 3. Trend & KPI deltas (from `RunHistory` — real history)

Helper columns on `RunHistory` (Data view → New column):

```DAX
QSort  = RunHistory[Run_Year] * 10 + VALUE ( SUBSTITUTE ( RunHistory[Run_Quarter], "Q", "" ) )
QLabel = RunHistory[Run_Quarter] & " '" & RIGHT ( FORMAT ( RunHistory[Run_Year], "0000" ), 2 )
```
Set `QLabel` **Sort by column → QSort**.

Trend measures (use `Count`, the pre-aggregated total):

```DAX
Run Total      = SUM ( RunHistory[Count] )
Run Priced     = CALCULATE ( [Run Total], RunHistory[Category] = "Priced" )
Run Not Priced = CALCULATE ( [Run Total], RunHistory[Category] = "Not Priced" )

Priced % (Q)     = DIVIDE ( [Run Priced],     [Run Total] )
Not Priced % (Q) = DIVIDE ( [Run Not Priced], [Run Total] )
```

Latest / previous quarter and deltas (computed, not hardcoded):

```DAX
Latest QSort =
    CALCULATE ( MAX ( RunHistory[QSort] ), ALLSELECTED ( RunHistory ) )

Latest Priced % =
    CALCULATE ( [Priced % (Q)],
        FILTER ( ALLSELECTED ( RunHistory ), RunHistory[QSort] = [Latest QSort] ) )

Prev Priced % =
    CALCULATE ( [Priced % (Q)],
        FILTER ( ALLSELECTED ( RunHistory ), RunHistory[QSort] = [Latest QSort] - 1 ) )

Priced Delta pp = ( [Latest Priced %] - [Prev Priced %] ) * 100

-- Not Priced (same pattern)
Latest Not Priced % =
    CALCULATE ( [Not Priced % (Q)],
        FILTER ( ALLSELECTED ( RunHistory ), RunHistory[QSort] = [Latest QSort] ) )
Prev Not Priced % =
    CALCULATE ( [Not Priced % (Q)],
        FILTER ( ALLSELECTED ( RunHistory ), RunHistory[QSort] = [Latest QSort] - 1 ) )
Not Priced Delta pp = ( [Latest Not Priced %] - [Prev Not Priced %] ) * 100

Avg Priced % =
    AVERAGEX ( VALUES ( RunHistory[QSort] ), [Priced % (Q)] )
```

Delta labels & colors for card reference labels:

```DAX
Priced Delta Label =
    VAR d = [Priced Delta pp]
    RETURN IF ( d >= 0, "▲ ", "▼ " ) & FORMAT ( ABS ( d ), "0.0" ) & "pp"

-- Priced: up is good
Priced Delta Color = IF ( [Priced Delta pp] >= 0, "#2ECC71", "#E74C3C" )

-- Not Priced: DOWN is good — flip it
Not Priced Delta Color = IF ( [Not Priced Delta pp] <= 0, "#2ECC71", "#E74C3C" )
```

> The original Overview KPIs show a small "vs prev qtr" delta too. Reuse `[Priced Delta pp]` etc. there —
> now driven by your real run history rather than the mock's fixed `+2.3 / -1.4 / +0.6 / -0.8`.

---

## 4. Donut center label

```DAX
Total Attrs (k) = FORMAT ( DIVIDE ( [Total Attrs], 1000 ), "0.0" ) & "k"
```

---

## 5. Summary-table "Priced %" data-bar color rule

Conditional formatting → Data bars → **color based on field** → use this measure:

```DAX
Priced % Bar Color =
    SWITCH ( TRUE (),
        [Priced %] < 0.50, "#E74C3C",   -- danger
        [Priced %] < 0.65, "#F39C12",   -- warn
        "#2ECC71"                         -- good
    )
```

---

## 6. Heat-matrix conditional formatting (color scale)

On each `%` measure: **Cell elements → Background color → Format style: Gradient**. Match the original
`cellStyle()` ramps — set **Minimum = Number 0** and **Maximum = Number** (the value below) so the gradient
saturates at the same point:

| Column        | Measure          | Min color (low) | Max color (high) | Max value |
|---------------|------------------|-----------------|------------------|-----------|
| Priced %      | `[Priced %]`     | `#EAF8F0`       | `#2ECC71`        | 0.85      |
| Not Priced %  | `[Not Priced %]` | `#FDECEA`       | `#E74C3C`        | 0.50      |
| Zero Priced % | `[Zero Priced %]`| `#FEF3E0`       | `#F39C12`        | 0.30      |
| Junk %        | `[Junk %]`       | `#EEF0F1`       | `#95A5A6`        | 0.30      |

Use a **two-color** scale (Center off). Keep cell font dark `#1f2937` for readability on saturated cells.

---

## 7. Attribute Detail measures (from `AttributeDetail`)

```DAX
Detail Row Count = COUNTROWS ( AttributeDetail )

-- Per-category counts for the tab strip pills
Detail Priced     = CALCULATE ( [Detail Row Count], AttributeDetail[Category] = "Priced" )
Detail Not Priced = CALCULATE ( [Detail Row Count], AttributeDetail[Category] = "Not Priced" )
Detail Zero       = CALCULATE ( [Detail Row Count], AttributeDetail[Category] = "Price in 0" )
Detail Junk       = CALCULATE ( [Detail Row Count], AttributeDetail[Category] = "Junk Price" )
```

Optional: only surface FP/TP/LP columns when an FP/TP/LP catalog is in context (drives a "show FP/TP/LP"
toggle/bookmark — I51 and I52 are the FP/TP/LP catalogs):

```DAX
Has FPLP Pricing =
    CALCULATE (
        COUNTROWS ( AttributeDetail ),
        AttributeDetail[Catalog] IN { "I51", "I52" },
        NOT ISBLANK ( AttributeDetail[FP] )
    ) > 0
```

> `Base_Price` / `FP` / `TP` / `LP` arrive pre-normalized in `attribute_detail.csv` (the pipeline maps each
> catalog's native price header onto these). Display them as table columns: I38/I53/I62 fill `Base_Price`,
> I51/I52 fill `FP/TP/LP`; the others are blank — which matches the source design.

---

## 8. Sorting

- `DimCategory[Category]` → **Sort by column → SortOrder** (1 Priced, 2 Not Priced, 3 Price in 0, 4 Junk Price).
- `RunHistory[QLabel]` → **Sort by column → QSort**.
- This keeps every legend, tab strip, and trend axis in canonical order.
```
