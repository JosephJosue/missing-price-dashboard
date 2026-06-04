# Pricing Coverage Dashboard — DAX Measures & Conditional Formatting

Companion to `PowerBI_Build_Guide.md`. Copy these measures into your model (a dedicated
`_Measures` table is recommended). Table/column names assume the model in §2 of the guide.

Conventions:
- Fact `Summary[Server, Country, Catalog, Modality, Priced, NotPriced, PriceInZero, JunkPrice]`
- Unpivoted `SummaryUnpivot[Server, Country, Catalog, Modality, Category, Count]`
- `Quarters[Server, Label, Year, Q, PricedPct, NotPricedPct]`
- `DimCategory[Category, SortOrder, Color]`

---

## 1. Base counts

```DAX
Priced       = SUM ( Summary[Priced] )
Not Priced   = SUM ( Summary[NotPriced] )
Zero Priced  = SUM ( Summary[PriceInZero] )
Junk Price   = SUM ( Summary[JunkPrice] )

Total Attrs  = [Priced] + [Not Priced] + [Zero Priced] + [Junk Price]
```

For the unpivoted visuals (donut, stacked column, matrix):

```DAX
Category Count = SUM ( SummaryUnpivot[Count] )
```

---

## 2. Coverage & share measures

```DAX
Coverage % = DIVIDE ( [Priced], [Total Attrs] )

-- Row-context share for the heat matrix (% within the current Country row, across all categories)
Priced %      = DIVIDE ( [Priced],      [Total Attrs] )
Not Priced %  = DIVIDE ( [Not Priced],  [Total Attrs] )
Zero Priced % = DIVIDE ( [Zero Priced], [Total Attrs] )
Junk %        = DIVIDE ( [Junk Price],  [Total Attrs] )

-- Generic "% of grand total" used in KPI card footers
Category % of Total =
    DIVIDE ( [Category Count], CALCULATE ( [Category Count], ALLSELECTED ( DimCategory ) ) )
```

---

## 3. KPI delta measures (vs previous quarter)

The original app uses fixed deltas. To reproduce the exact numbers, hardcode them:

```DAX
Priced Delta      = 2.3
Not Priced Delta  = -1.4
Zero Delta        = 0.6
Junk Delta        = -0.8
```

To compute them dynamically from `Quarters` instead:

```DAX
Latest Q Rank =
    MAXX ( ALL ( Quarters ), Quarters[Year] * 10 + Quarters[Q] )

Latest Priced % =
    CALCULATE ( MAX ( Quarters[PricedPct] ),
        FILTER ( ALL ( Quarters ), Quarters[Year] * 10 + Quarters[Q] = [Latest Q Rank] ) )

Prev Priced % =
    CALCULATE ( MAX ( Quarters[PricedPct] ),
        FILTER ( ALL ( Quarters ), Quarters[Year] * 10 + Quarters[Q] = [Latest Q Rank] - 1 ) )

Priced Delta pp = ( [Latest Priced %] - [Prev Priced %] ) * 100

-- Same pattern for Not Priced:
Latest Not Priced % =
    CALCULATE ( MAX ( Quarters[NotPricedPct] ),
        FILTER ( ALL ( Quarters ), Quarters[Year] * 10 + Quarters[Q] = [Latest Q Rank] ) )

Avg Priced % = AVERAGEX ( ALL ( Quarters ), Quarters[PricedPct] )
```

Delta indicator label (▲/▼) for a card reference label:

```DAX
Priced Delta Label =
    VAR d = [Priced Delta pp]
    RETURN IF ( d >= 0, "▲ " & FORMAT ( ABS ( d ), "0.0" ) & "pp",
                        "▼ " & FORMAT ( ABS ( d ), "0.0" ) & "pp" )

Priced Delta Color = IF ( [Priced Delta pp] >= 0, "#2ECC71", "#E74C3C" )
```

> Note: for **Not Priced**, "good" is a *decrease*, so flip the color logic:
> `IF ( [NP Delta] <= 0, "#2ECC71", "#E74C3C" )`.

---

## 4. Donut center label (total in thousands)

```DAX
Total Attrs (k) = FORMAT ( DIVIDE ( [Total Attrs], 1000 ), "0.0" ) & "k"
```

---

## 5. Summary-table "Priced %" data-bar color rule

Use as a **field-value** color in Conditional formatting → Data bars → "color based on field":

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

Apply **Background color → Format style: Gradient** on each percentage measure. Match the
original `cellStyle()` ramps (alpha 0.08 → 0.70 over the listed max):

| Column        | Measure          | Min color (low)      | Max color (high) | Max value |
|---------------|------------------|----------------------|------------------|-----------|
| Priced %      | `[Priced %]`     | `#EAF8F0` (≈8% green)| `#2ECC71`        | 0.85      |
| Not Priced %  | `[Not Priced %]` | `#FDECEA`            | `#E74C3C`        | 0.50      |
| Zero Priced % | `[Zero Priced %]`| `#FEF3E0`            | `#F39C12`        | 0.30      |
| Junk %        | `[Junk %]`       | `#EEF0F1`            | `#95A5A6`        | 0.30      |

In each column's color-scale dialog set **Minimum = Number 0**, **Maximum = Number** (the value above),
so the gradient saturates at the same point the React app does. Set **Center** off (two-color scale).

Font color for readability on dark cells — add a separate **Font color** rule:

```DAX
Priced % Font = IF ( DIVIDE ( [Priced], [Total Attrs] ) > 0.55, "#1f2937", "#1f2937" )
```

(The original keeps text dark `#1f2937` on saturated cells.)

---

## 7. Quarterly trend — target line

For the "Not Priced %" detail chart, add an **Analytics → Constant line** at `0.18`
labeled `target ≤ 18%`, color `#9ca3af`, dashed.

---

## 8. Sorting

- Mark `DimCategory[SortOrder]` (1=Priced, 2=Not Priced, 3=Zero, 4=Junk) as **Sort by column** for `Category`
  so legends and tabs always render in the canonical order.
- Sort `Quarters[Label]` by `Year * 10 + Q` (create that as a calculated column `QSort`).
