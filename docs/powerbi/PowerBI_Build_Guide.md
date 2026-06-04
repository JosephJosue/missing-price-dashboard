# Pricing Coverage Dashboard — Power BI Replication Guide

A step-by-step guide to rebuild the React/HTML "Pricing Coverage Dashboard" in Power BI Desktop, matching the exact layout, palette, and visuals.

---

## 0. Design reference (what we're matching)

**Three report pages**, a dark-navy header + left sidebar, a white filter bar, and a
green/red/amber/grey classification palette.

| Token            | Hex        | Meaning            |
|------------------|------------|--------------------|
| Priced           | `#2ECC71`  | KPI green / good   |
| Not Priced       | `#E74C3C`  | KPI red / bad      |
| Price in 0 (Zero)| `#F39C12`  | KPI amber          |
| Junk Price       | `#95A5A6`  | KPI grey           |
| Accent (blue)    | `#3b82f6`  | links, selection   |
| Brand blue       | `#4f86c6`  | logo, avatar, nav  |
| Header / sidebar | `#1e2a3a` / `#243447` | dark chrome |
| Page background  | `#f3f4f6`  | canvas             |
| Card background  | `#ffffff`  | visual fill        |
| Border           | `#e5e7eb`  | card border (6px radius) |
| Text / muted / light | `#1f2937` / `#6b7280` / `#9ca3af` | |

Font everywhere: **Segoe UI** (Power BI default — perfect match). Body 13px, KPI value 28px bold,
page title 18px semibold.

---

## 1. Canvas & theme setup

1. **File → Options & settings → Options → Report settings**: enable *"Change default visual interaction…"* and the new card/slicer visuals.
2. **View → Page size → Custom**: `1280 × 720` (16:9). Page view = *Fit to page*.
3. **Format page → Canvas background**: color `#f3f4f6`, transparency `0%`.
4. **View → Themes → Browse for themes** → import **`PricingCoverage_Theme.json`** (shipped alongside this guide). This locks in the palette, 6px rounded white cards with `#e5e7eb` borders, and Segoe UI text classes.

---

## 2. Data model

The source app generates mock data with `genServerData()`. Reproduce the same shape — whether you
load the real classifier output or recreate the mock. Build these tables:

### 2.1 `Summary` (fact — country × catalog × modality, per server)
Columns: `Server` (RF/HOS), `Country`, `Catalog` (I38/I51/I52/I53/I62), `Modality` (CT/MR/XR/US/NM/PT/MG/IO),
`Priced`, `NotPriced`, `PriceInZero`, `JunkPrice` (integer counts).

> **Recommended:** also create an unpivoted version for the stacked/donut visuals.
> In Power Query, select the four count columns → **Unpivot Columns** → rename to
> `Category` / `Count`. Call this query **`SummaryUnpivot`**.

### 2.2 `Attributes` (detail / drill-through)
Columns: `Id`, `Server`, `Country`, `AttrCode` (e.g. `AVC-I52-48213`), `ModalityCode` (e.g. `CT417`),
`ModalityType`, `Catalog`, `Category`, `BasePrice`, and the I52-only fields `FP`, `TP`, `LP`.

### 2.3 `Quarters` (trend)
Columns: `Server`, `Label` (`Q1 '23`…), `Year`, `Q`, `PricedPct`, `NotPricedPct` (decimals 0–1).

### 2.4 Dimension tables (for clean slicers & coloring)
- **`DimCategory`**: `Category`, `SortOrder` (1–4), `Color` (the four hex values above).
- **`DimCountry`** (70 ISO codes), **`DimCatalog`** (5), **`DimModality`** (8), **`DimServer`** (RF, HOS).

**Relationships:** join the dims to `Summary`, `SummaryUnpivot`, and `Attributes` on the matching keys
(single direction, 1→*). Mark `DimCategory[SortOrder]` as the sort-by column for `Category`.

---

## 3. Core DAX measures

```DAX
Total Attrs      = SUM ( Summary[Priced] ) + SUM ( Summary[NotPriced] )
                 + SUM ( Summary[PriceInZero] ) + SUM ( Summary[JunkPrice] )

Priced           = SUM ( Summary[Priced] )
Not Priced       = SUM ( Summary[NotPriced] )
Zero Priced      = SUM ( Summary[PriceInZero] )
Junk Price       = SUM ( Summary[JunkPrice] )

-- For the unpivoted model (donut, stacked bar, matrix):
Category Count   = SUM ( SummaryUnpivot[Count] )
Coverage %       = DIVIDE ( [Priced], [Total Attrs] )

-- Generic "% of total" used in KPI footers and the heat matrix:
Category % of Total =
    DIVIDE ( [Category Count], CALCULATE ( [Category Count], ALL ( DimCategory ) ) )

-- Quarter deltas (Trend page KPIs):
Latest Priced %  = CALCULATE ( MAX ( Quarters[PricedPct] ),
                     TOPN ( 1, Quarters, Quarters[Year]*10 + Quarters[Q], DESC ) )
```

> The original mock uses *static* deltas (`Priced +2.3%`, `Not Priced −1.4%`, …). If you want the same
> numbers exactly, hardcode them in a small `Deltas` table; otherwise compute period-over-period with `Quarters`.

---

## 4. Page chrome (shared on all 3 pages)

Power BI has no fixed header/sidebar, so build them with shapes + buttons and **copy them onto every page**.

### 4.1 Top header bar (`1280 × 56`, at x0 y0)
- **Rectangle**: fill `#1e2a3a`.
- **Logo**: rounded rectangle `26×26`, gradient `#4f86c6 → #2ECC71` (135°), white "PC" text.
- **Title text box**: "Pricing Coverage Dashboard" (white, 15px semibold) + breadcrumb "/ Catalog Analytics / Q2 2025" (`rgba(255,255,255,.55)`, 12px).
- **Server toggle (RF / HOS):** see §7 — two buttons bound to bookmarks, or a single-select slicer styled as tiles.
- **Right side:** bell + download **Button** icons, then an avatar circle `#4f86c6` "AT" + "Analytics Team".

### 4.2 Left sidebar (`220 × 664`, at x0 y56)
- **Rectangle**: fill `#243447`.
- **Nav items** (3 **Buttons**, each bound to a page-navigation action):
  1. **Overview** — *KPIs & distribution*
  2. **Attribute Detail** — *Drill-through list*
  3. **Quarterly Trend** — *Time series*
  Active state: left border `#4f86c6` (3px), background `rgba(255,255,255,.08)`, white bold text, numbered `22×22` chip.
- **Data Source block:** green "live dot", server name, `5 catalog files · Python classifier v3.2`.
- **Footer meta** (bottom): *Last refresh* `27 May 2026, 09:42 GMT`, *Attributes scanned* `[Total Attrs]`, *Coverage* `[Coverage %]` in green, build string.

### 4.3 Filter bar (`1060 × 44`, white, below header to the right of sidebar)
- White rectangle, bottom border `#e5e7eb`.
- "FILTERS" label + three **Slicers**: **Country**, **Catalog File**, **Modality**.
  Format each slicer → **dropdown** style, multi-select with "Select All". Border `#d1d5db`, 4px radius.
- A **Reset filters** button (calls a "clear all slicers" bookmark) and a **Refresh** button on the far right.

> Tip: group the header, sidebar, and filter bar, then **Ctrl+C / Ctrl+V across pages** to keep them pixel-identical.

---

## 5. Page 1 — Overview

Layout top-to-bottom: KPI row → (Donut | Stacked bar) → Heat matrix → Summary table.

### 5.1 KPI row — 4 cards (`repeat(4, 1fr)`, 12px gap)
Each original card shows: name + colored dot, big value, "▲/▼ delta vs prev qtr", "% of total", and a progress bar with a colored **4px left border**.

Best Power BI match — use the **new Card visual** (one per category) :
- **Fields:** the category measure (`[Priced]`, `[Not Priced]`, `[Zero Priced]`, `[Junk Price]`).
- **Reference labels:** add `[Category % of Total]` → "% of total", and the delta measure → show ▲/▼ with conditional color (green up / red down).
- **Callout value:** 28px bold, color `#1f2937`.
- **Accent / left border:** Format → Effects → enable a colored left border (or place a `4px` rectangle on the card's left edge) using the matching category color.
- **Progress bar:** add a thin `100%`-wide **stacked bar** or a measure-driven bar set to `% of total` width, track color `#f3f4f6`, fill = category color.

> Simpler alternative: a single **Matrix** with one row per category, data bars on the value column, and conditional font color from `DimCategory[Color]`.

### 5.2 Donut — "Category Distribution" (left card, ~380px wide)
- **Donut chart**: Legend/Details = `Category`, Values = `[Category Count]`.
- **Inner radius** ~ 60% (matches the thin ring). Center has total `xx.x k` + "TOTAL ATTRS" — add a **Card** on top of the hole showing `[Total Attrs]` formatted in thousands.
- **Data colors:** set each `Category` to its hex (Format → Data colors → per category).
- Detail labels = **Percent of total**, 1 decimal. Right-side legend with % values mirrors the original `donut-legend`.

### 5.3 Stacked bar — "Top 10 Countries — Coverage" (right card)
- **Stacked column chart**: Axis = `Country`, Legend = `Category`, Values = `[Category Count]`.
- **Top-N filter:** filter pane → `Country` → Top N = 10 by `[Total Attrs]`.
- Data colors per category as above. Y-axis 4 gridlines, gridline color `#f3f4f6`.
- Turn **on** total data labels (the original prints each country's total above the bar).

### 5.4 Heat matrix — "Country Heat Matrix" (full width, scrollable)
- **Matrix visual**: Rows = `Country`; Values = `Priced %`, `Not Priced %`, `Zero Priced %`, `Junk %` (each a `DIVIDE(category, row total)` measure), plus `[Total Attrs]`.
- **Conditional formatting → Background color** on each % column (Format → Cell elements → Background color → *Color scale*):
  - Priced %: min `rgba(46,204,113,.08)` → max `#2ECC71` (scale 0→85%).
  - Not Priced %: white → `#E74C3C` (0→50%).
  - Zero %: white → `#F39C12` (0→30%).
  - Junk %: white → `#95A5A6` (0→30%).
  - Set font to dark `#1f2937` on high-intensity cells.
- Enable column headers sticky, row height compact. Add a final **"Coverage Bar"** column using a `100%` stacked bar measure if you want the inline stacked mini-bar (optional — Power BI matrices don't do inline stacked bars natively, so use a measure-driven bar chart small multiple or skip).
- Header row fill `#f9fafb`, uppercase 11px.

### 5.5 Summary table — "Coverage Summary — Country × Catalog"
- **Table** (or Matrix): columns `Country`, `Catalog`, `Priced`, `Not Priced`, `Zero Priced`, `Junk`, `Total`, `Priced %`.
- Color each count column's font with its category color.
- **Priced %** column → **Data bars** (Conditional formatting → Data bars): green, with rule-based color — `< 50%` red `#E74C3C`, `50–65%` amber `#F39C12`, else green `#2ECC71`.
- Catalog code styled as a mono "pill" — emulate with a light grey background via conditional formatting.
- Enable paging look via table's built-in scroll (Power BI auto-paginates).

---

## 6. Page 2 — Attribute Detail (drill-through)

### 6.1 Category tab strip
Original = 4 pill tabs (Priced / Not Priced / Price in 0 / Junk Price) with live counts, active tab filled with the category color.
- Implement with a **slicer** on `DimCategory[Category]` set to **single-select**, **horizontal/tile** orientation, with selected-tile fill = category color. To get the per-tab count, add a small **multi-row card** or place count labels.
- Alternatively use **4 bookmark buttons** (more control over the exact filled-pill look).

### 6.2 Search + export
- Power BI has no free-text search box on a table by default. Use a **Text slicer** (search-enabled slicer on `AttrCode`) or the visual's built-in search. Place an **Export filtered list** button (the table's "…" menu already exports to CSV).

### 6.3 The drill-through table
- **Table visual**, columns in order: `Country`, `Attribute Value Code`, `Modality Code`, `Base Price`, `Catalog Source`.
- **I52 special case:** when the Priced tab is active and rows are catalog I52, the source shows 3 extra columns **FP / TP / LP** (accent blue `#3b82f6`). Implement as separate measures shown conditionally, or a second table behind a bookmark that swaps in when `Catalog = I52`.
- Mono font (Consolas) for `AttrCode`/`ModalityCode`; catalog source as a blue pill (`#eef2ff` bg, `#4338ca` text) via conditional formatting.
- Page size = 14 rows in the original; Power BI tables scroll — fine to leave native paging.

### 6.4 Make it a real drill-through (optional but recommended)
Add `Country` and `Category` to the page's **Drill-through** well so users right-click a bar/KPI on the
Overview page → *Drill through → Attribute Detail*, carrying the filter context.

---

## 7. Page 3 — Quarterly Trend

### 7.1 Three KPI cards (`repeat(3, 1fr)`)
- **Latest Priced %** (green) with ▲/▼ `pp` delta vs prior quarter + progress bar.
- **Latest Not Priced %** (red) — note delta is "good" when it goes *down*.
- **Avg Priced %** (brand blue `#4f86c6`) "over N qtrs".
Build the same way as §5.1 (new Card + reference labels + bar).

### 7.2 Main combo chart — "Priced Coverage by Quarter"
- **Line and stacked/clustered column chart**:
  - Shared axis = `Quarters[Label]` (sorted by `Year*10+Q`).
  - **Column values** = `[Latest Priced %]`/`PricedPct` → green bars `#2ECC71`, 85% opacity, data labels in dark green `#1e8449`.
  - **Line values** = `NotPricedPct` → red dashed line `#E74C3C` (set line style = dashed, width 2).
- Add a second **Area/line** for the Priced trend line in dark green `#1e8449` with a soft green gradient fill (Power BI: line chart with shade-area on). Y-axis 0–100%, ticks at 0/25/50/75/100, gridlines `#f3f4f6`.
- Year separators: the original draws dashed verticals between years — optional; you can add a constant-line or just rely on the year grouping on the axis.

### 7.3 Secondary chart — "Not Priced % — Trend Detail"
- **Area chart**: `Quarters[Label]` × `NotPricedPct`, color `#E74C3C` with gradient fill, Y-axis 0–50%.
- Add a **constant line** at `18%` labeled "target ≤ 18%".

### 7.4 Note box
- A rectangle fill `#fff8e1`, left border `#f6c343` (3px), text `#6e4f00`:
  *"Data sourced from quarterly script runs of the Python classifier (v3.2)…"*. Use a Text box.

---

## 8. The Server (RF / HOS) toggle — the one cross-cutting interaction

The app swaps the **entire dataset** between server `RF` and `HOS`. Two clean Power BI options:

**Option A — Slicer (simplest):** single-select slicer on `DimServer[Server]`, tile orientation,
placed in the header. Selected tile filled white/`#1e2a3a` to mimic the toggle. All visuals filter automatically
because every fact table has a `Server` column related to `DimServer`.

**Option B — Bookmarks (exact look):** two header **Buttons** ("RF · Rightfit", "HOS"). Create two
bookmarks that (a) set the `DimServer` slicer selection and (b) swap each button's on/off style. Bind each
button's action to its bookmark. This reproduces the pill-toggle styling precisely.

---

## 9. Final polish checklist

- [ ] All cards: white fill, `#e5e7eb` 1px border, **6px corner radius**, subtle shadow (Effects → Shadow, low).
- [ ] Card titles 13px Segoe UI Semibold `#1f2937`; subtitles 11px `#6b7280`.
- [ ] Category colors applied **identically** in every visual (donut, stacked bar, KPIs, matrix, table fonts).
- [ ] Tooltips: enable, dark style (`#1e2a3a`, white text) to match the app's custom tooltip.
- [ ] Turn **off** visual headers in view mode (Format → Header icons) for the clean look.
- [ ] Edit interactions so the Country/Catalog/Modality slicers cross-filter all visuals, but the Server slicer filters everything.
- [ ] Group + copy the header/sidebar/filter bar onto all 3 pages so navigation is consistent.
- [ ] Save as **.pbix**; optionally publish and pin the Overview KPIs to a dashboard.

---

### Visual-to-Power-BI mapping (quick reference)

| App element                         | Power BI visual                                  |
|-------------------------------------|--------------------------------------------------|
| KPI cards (value + Δ + bar)         | New **Card** + reference labels + left accent    |
| Category Distribution donut         | **Donut chart** + center Card overlay            |
| Top 10 Countries stacked            | **Stacked column chart** + Top-N filter          |
| Country Heat Matrix                 | **Matrix** + color-scale conditional formatting  |
| Coverage Summary table              | **Table** + data bars + rule-based colors        |
| Attribute Detail list + tabs        | **Table** + single-select tile **slicer** / bookmarks |
| Quarterly combo (bars + line + area)| **Line and clustered column chart** (+area line) |
| Not Priced trend                    | **Area chart** + constant line at 18%            |
| Country / Catalog / Modality filters| **Slicers** (dropdown, multi-select)             |
| Server RF/HOS toggle                | Single-select **slicer** or **bookmark buttons** |
