# Pricing Coverage Dashboard — Power BI Build Guide (Real Data)

A start-to-finish walkthrough for building the **Pricing Coverage Dashboard** in Power BI Desktop,
connected to your live pipeline outputs on **SharePoint**. It matches the original React/HTML design's
layout, palette, and visuals.

This guide assumes the data produced by `dashboard_export.py` and the per-catalog classifier CSVs.

---

## 0. Design reference (the look we're matching)

Three pages, a dark-navy header + left sidebar, a white filter bar, light-grey canvas, and a
green/red/amber/grey classification palette.

| Token            | Hex        | Used for           |
|------------------|------------|--------------------|
| Priced           | `#2ECC71`  | green / good       |
| Not Priced       | `#E74C3C`  | red / bad          |
| Price in 0       | `#F39C12`  | amber              |
| Junk Price       | `#95A5A6`  | grey               |
| Accent (blue)    | `#3b82f6`  | links, selection   |
| Brand blue       | `#4f86c6`  | logo, avatar, nav  |
| Header / sidebar | `#1e2a3a` / `#243447` | dark chrome |
| Page background  | `#f3f4f6`  | canvas             |
| Card / border    | `#ffffff` / `#e5e7eb` (6px radius) | visuals |
| Text / muted / light | `#1f2937` / `#6b7280` / `#9ca3af` | |

Font: **Segoe UI** (Power BI default). KPI value 28px bold, page title 18px semibold.

---

## 1. Before you start

1. Install/open **Power BI Desktop** (latest). Sign in with your **organizational (Philips) account** —
   you'll need it for SharePoint.
2. **View → Page size → Custom** → `1280 × 720`. Set page view to **Fit to page**.
3. **View → Themes → Browse for themes** → import **`PricingCoverage_Theme.json`** (next to this file).
   This applies the palette, Segoe UI text, and the 6px rounded white card style automatically.
4. **File → Options → Preview features**: make sure the **new Card visual** and **on-object interaction**
   are on (used for the KPI cards).

---

## 2. Your three pipeline outputs (what we connect to)

`dashboard_export.py` writes, **per server**, into `<BASE_DIR>/<SERVER>/Output/`:

| File | Location | Grain | Powers |
|------|----------|-------|--------|
| `dashboard_feed.csv` | `…/<SERVER>/Output/Dashboard/` | **one row per attribute** (Server, Catalog, Category, Country, Attribute_Code, Modality_Code, Run_Date, Run_Quarter, Run_Year) — overwritten each run | **Page 1 Overview** aggregates |
| `run_history.csv` | `…/<SERVER>/Output/Dashboard/` | **pre-aggregated counts** (Server, Run_Date, Run_Quarter, Run_Year, Catalog, Category, Count) — appended each run | **Page 3 Trend** |
| per-catalog category CSVs | `…/<SERVER>/Output/<CATALOG>/<CATALOG>_<suffix>.csv` (e.g. `I52_priced.csv`) — native columns incl. prices & I52 FP/TP/LP | one row per attribute, **native schema** | **Page 2 Attribute Detail** |

Two important facts that shape the model:

- **`dashboard_feed.csv` is already "long".** It has a `Category` column with one row per attribute, so
  there is **no unpivot step**. Counts come from `COUNTROWS`.
- The feed carries only classification + identity (no prices). The **prices and I52 FP/TP/LP live in the
  native per-catalog CSVs**, so the Detail page reads those directly.

The category file suffixes map to labels (from `CATEGORY_MAP`):
`priced → Priced`, `not_priced → Not Priced`, `zero_priced → Price in 0`, `junk_price → Junk Price`.
Missing modality/country come through as the literal **`N/A`** (the pipeline's `MISSING_VALUE`).

---

## 3. Connect to SharePoint and combine the server pair

### 3.1 Open the SharePoint folder connector
**Home → Get data → More… → SharePoint folder → Connect.**

When prompted for the **Site URL**, paste the **site root**, *not* the deep document path. For example:
`https://philips.sharepoint.com/sites/PSTActivities`
(not `…/BI Connector/RF/Output/...`). Sign in with **Organizational account** → **Connect**.

Power BI returns one big table listing **every file in the site**. Click **Transform Data** (not Load) to
open the Power Query Editor — we'll filter from here.

### 3.2 Query A — `DashboardFeed` (combine both `dashboard_feed.csv`)

1. In Power Query, the query is probably called `SharePoint`/`Site`. Right-click it → **Reference**, rename
   the reference to **`DashboardFeed`**. (Working from a reference keeps the raw file list reusable for the
   other two queries.)
2. **Filter `Name`** → equals `dashboard_feed.csv`. You should be left with **2 rows** — the RF copy and
   the HOS copy (their `Folder Path` differs: `…/RF/Output/Dashboard/` vs `…/HOS/Output/Dashboard/`).
3. **(Safety net) derive the server from the path** *before* combining. **Add Column → Custom Column**:
   ```m
   ServerFromPath =
       if Text.Contains([Folder Path], "/RF/")  then "RF"
       else if Text.Contains([Folder Path], "/HOS/") then "HOS"
       else "UNKNOWN"
   ```
   This is your "merge each file with its server pair" guarantee — even though each row already contains a
   `Server` column written by the pipeline, this proves the file came from the right folder.
4. **Combine the files.** Click the **Combine Files** icon (⤓ double-arrow) on the **Content** column →
   **OK**. Power BI generates a sample transform and stacks both CSVs into one table. The `Server` column
   (already inside each file) now reads `RF` for RF rows and `HOS` for HOS rows automatically.
5. **Validate, then drop the helper.** Add a quick check column `if [Server] = [ServerFromPath] then "ok"
   else "MISMATCH"`, confirm everything says `ok`, then remove both helper columns. (If you don't fully
   trust the in-file value, keep `ServerFromPath` and use *it* as your server field instead.)
6. **Set data types** (Power Query guesses wrong on codes):
   - Text: `Server`, `Catalog`, `Category`, `Country`, `Attribute_Code`, `Modality_Code`, `Run_Quarter`
   - Whole number: `Run_Year`
   - Date: `Run_Date` (`YYYY-MM-DD`)
   - The files are `utf-8-sig`; `Csv.Document` with **encoding 65001** strips the BOM. If the first header
     shows a stray ``, fix the encoding in the auto-generated **Transform Sample File** step.
7. Keep **`N/A`** in `Country`/`Modality_Code` as a real value (don't blank it) — it becomes one tidy,
   hideable slicer entry.

### 3.3 Query B — `RunHistory` (combine both `run_history.csv`)

Same recipe: **Reference** the file list → rename **`RunHistory`** → filter `Name = run_history.csv` →
combine. Types: `Count` and `Run_Year` → Whole number; `Run_Date` → Date; the rest Text. The `Server`
column is again already in each file.

> Because `run_history.csv` is **appended every run**, this table is your genuine time series — use it for
> the Trend page and for real "vs previous quarter" KPI deltas (no hardcoded numbers needed).

### 3.4 Query C — `AttributeDetail` (combine the native per-catalog CSVs)

This is the richer source for Page 2 — it has the **prices** and the **I52 FP/TP/LP** columns.

1. **Reference** the file list again → rename **`AttributeDetail`**.
2. Filter to just the native category files. The simplest robust filter:
   - `Extension` equals `.csv`, **and**
   - `Name` does **not** equal `dashboard_feed.csv`, **and** `Name` does **not** equal `run_history.csv`.
   That leaves files like `I38_priced.csv`, `I52_not_priced.csv`, etc., under each `…/Output/<CATALOG>/`.
3. **Derive keys from the path/filename** (don't rely on combine to infer them). Add Custom Columns:
   ```m
   Server   = if Text.Contains([Folder Path], "/RF/") then "RF"
              else if Text.Contains([Folder Path], "/HOS/") then "HOS" else "UNKNOWN"
   Catalog  = Text.BeforeDelimiter([Name], "_")                       // "I52"
   CatSuffix = Text.BeforeDelimiter(Text.AfterDelimiter([Name], "_", 0), ".csv")  // "not_priced"
   Category = let m = [CatSuffix] in
                if m = "priced" then "Priced"
                else if m = "not_priced" then "Not Priced"
                else if m = "zero_priced" then "Price in 0"
                else if m = "junk_price" then "Junk Price" else m
   ```
   > Note: for suffixes with two underscores (`not_priced`, `zero_priced`, `junk_price`) the simpler
   > `Text.AfterDelimiter([Name], "_")` already returns `not_priced.csv`; strip `.csv` with
   > `Text.BeforeDelimiter(…, ".csv")`. The lookup above maps it to the display label.
4. **Combine carefully — the native CSVs have different columns per catalog** (I38/I51/I52/I53 use
   `Attribute Value Code` + `Modality Code`; I62 uses `CVG Code` and has no modality; I52 priced adds
   FP/TP/LP). The auto "Combine Files" samples the *first* file and can drop columns that only exist in
   others. To union **all** columns safely:
   - After combining, click the **expand** control on the parsed table column and choose **“Load more”** so
     Power BI scans every file's headers before you expand — tick **all** columns, untick "use original
     column name as prefix".
   - *Or* do it explicitly: add a column `Parsed = Csv.Document([Content], [Delimiter=",", Encoding=65001,
     QuoteStyle=QuoteStyle.Csv])`, promote headers on the sample, then use **Table.Combine** which unions
     columns and fills missing ones with `null`.
5. **Normalize the key columns** so the page is catalog-agnostic. Add:
   ```m
   AttributeCode = if [Attribute Value Code] <> null then [Attribute Value Code] else [#"CVG Code"]
   ```
   Keep `Country`, `Modality Code` (null/`N/A` for I62), and whichever **price columns** exist in your
   native files — e.g. a base price column, and `FP` / `TP` / `LP` for I52. Rename them to clean names
   (`Base Price`, `FP`, `TP`, `LP`).
   > I can't see your exact native price header names from the pipeline code — after the combine, look at
   > the unioned column list and rename the price/FP/TP/LP columns to match the table in §6. Everything
   > else (Server, Catalog, Category, Country, Attribute code, Modality) is already covered above.
6. Set types: keep price/FP/TP/LP as **Text** if they can contain `—`, `$0.00`, or junk values like
   `-9999`; add a numeric copy via `try Number.FromText(...) otherwise null` only if you need to sort by price.

### 3.5 Build dimension tables

Clean slicers and one place to control colors/order. The fastest way: **Reference** `DashboardFeed`, keep
one column, **Home → Remove Rows → Remove Duplicates**.

- **`DimServer`** = distinct `Server` (`RF`, `HOS`)
- **`DimCountry`** = distinct `Country`
- **`DimCatalog`** = distinct `Catalog` (`I38, I51, I52, I53, I62`)
- **`DimModality`** = distinct `Modality_Code` (includes `N/A`)
- **`DimCategory`** — type it by hand (**Home → Enter data**):

  | Category | SortOrder | Color |
  |----------|-----------|-------|
  | Priced | 1 | `#2ECC71` |
  | Not Priced | 2 | `#E74C3C` |
  | Price in 0 | 3 | `#F39C12` |
  | Junk Price | 4 | `#95A5A6` |

  Then in **Data view**: select `Category` → **Column tools → Sort by column → SortOrder** so legends and
  tabs always render in canonical order.

Click **Home → Close & Apply** to load everything.

### 3.6 Relationships (Model view)

Drag to connect, all **single-direction, one-to-many** (dimension → fact):

```
DimServer[Server]      → DashboardFeed, RunHistory, AttributeDetail
DimCountry[Country]    → DashboardFeed, AttributeDetail
DimCatalog[Catalog]    → DashboardFeed, RunHistory, AttributeDetail
DimModality[Modality]  → DashboardFeed[Modality_Code], AttributeDetail[Modality Code]
DimCategory[Category]  → DashboardFeed[Category], RunHistory[Category], AttributeDetail[Category]
```

Gotchas:
- **`DimServer` is the spine** — because all three facts join to it, the single RF/HOS toggle (§8) filters
  every page at once.
- Keep cross-filter **single**. Both `DashboardFeed` and `AttributeDetail` sit at attribute grain and share
  the same dims — that's fine; each page just uses the fact it needs.
- The Modality join uses `Modality_Code` (which is `N/A` where the pipeline had no modality).

### 3.7 Sanity check before you build visuals

Drop a quick **Table**: `DimCountry[Country]` + a measure `=COUNTROWS(DashboardFeed)`, add a **Server**
slicer. Toggle RF/HOS — totals should change. Add Catalog/Modality slicers — everything should cross-filter.
When that behaves, the model is sound.

---

## 4. Core measures

Create them now from **`DAX_Measures.md`** (the companion file) — it's written for this exact
`DashboardFeed` / `RunHistory` / `AttributeDetail` model (`COUNTROWS`-based counts, real history deltas).
Put them on a dedicated `_Measures` table (Home → Enter data → empty table named `_Measures`).

---

## 5. Page chrome (shared on all 3 pages)

Power BI has no native header/sidebar, so build them once with shapes + buttons and **copy to every page**.

### 5.1 Header bar (`1280 × 56`, x0 y0)
- **Rectangle** fill `#1e2a3a`.
- **Logo**: rounded rectangle `26×26`, gradient `#4f86c6 → #2ECC71` (135°), white "PC".
- **Title** "Pricing Coverage Dashboard" (white, 15px semibold) + breadcrumb "/ Catalog Analytics / Q2 2025"
  (`rgba(255,255,255,.55)`, 12px).
- **Server toggle** (RF / HOS) — see §8.
- Right side: bell + download **Button** icons, avatar circle `#4f86c6` "AT" + "Analytics Team".

### 5.2 Sidebar (`220 × 664`, x0 y56)
- **Rectangle** fill `#243447`.
- Three nav **Buttons** with page-navigation actions:
  1. **Overview** — *KPIs & distribution*
  2. **Attribute Detail** — *Drill-through list*
  3. **Quarterly Trend** — *Time series*
  Active state: 3px left border `#4f86c6`, bg `rgba(255,255,255,.08)`, white bold, numbered `22×22` chip.
- **Data Source** block: green "live dot", server name, `5 catalog files · Python classifier v3.2`.
- **Footer meta**: *Last refresh* (use `=MAX(RunHistory[Run_Date])`), *Attributes scanned* `[Total Attrs]`,
  *Coverage* `[Coverage %]` in green.

### 5.3 Filter bar (`1060 × 44`, white)
- White rectangle, bottom border `#e5e7eb`.
- "FILTERS" label + three **Slicers** (dropdown style, multi-select with Select All): **Country**
  (`DimCountry`), **Catalog File** (`DimCatalog`), **Modality** (`DimModality`). Border `#d1d5db`, 4px radius.
- A **Reset filters** button (a bookmark that clears the slicers) and a **Refresh** button on the right.

> Group the header + sidebar + filter bar, then **Ctrl+C / Ctrl+V across all 3 pages** for pixel-identical chrome.

---

## 6. Page 1 — Overview  *(source: `DashboardFeed`)*

Layout top→bottom: KPI row → (Donut | Stacked bar) → Heat matrix → Summary table.

### 6.1 KPI row — 4 cards
Each shows: name + colored dot, big value, "▲/▼ delta vs prev qtr", "% of total", and a progress bar with a
4px colored left border. Use the **new Card visual**, one per category:
- **Fields:** `[Priced]`, `[Not Priced]`, `[Zero Priced]`, `[Junk Price]` (from the DAX file).
- **Reference labels:** add `[<cat> % of Total]` ("% of total") and the delta measure (▲/▼, conditional
  green/red). Callout 28px bold `#1f2937`.
- **Accent + bar:** colored 4px rectangle on the left edge; a thin measure-driven bar (track `#f3f4f6`,
  fill = category color) for the progress effect.

### 6.2 Donut — "Category Distribution"
- **Donut chart**: Legend = `DimCategory[Category]`, Values = `[Total Attrs]`. Inner radius ~60%.
- Set each category's **Data color** to its hex. Detail labels = **Percent of total**, 1 decimal.
- Center: overlay a **Card** showing `[Total Attrs (k)]` + "TOTAL ATTRS".

### 6.3 Stacked column — "Top 10 Countries — Coverage"
- **Stacked column chart**: Axis = `DimCountry[Country]`, Legend = `DimCategory[Category]`, Values = `[Total Attrs]`.
- Filter pane → `Country` → **Top N = 10** by `[Total Attrs]`. Category data colors as above. Turn on total
  data labels. Y gridlines `#f3f4f6`.

### 6.4 Heat matrix — "Country Heat Matrix"
- **Matrix**: Rows = `Country`; Values = `[Priced %]`, `[Not Priced %]`, `[Zero Priced %]`, `[Junk %]`, `[Total Attrs]`.
- **Conditional formatting → Background color (gradient)** per § DAX_Measures §6, with the listed min/max
  hex and saturation points. Keep dark text on saturated cells. Sticky headers, compact rows, header fill `#f9fafb`.

### 6.5 Summary table — "Coverage Summary — Country × Catalog"
- **Table/Matrix**: `Country`, `Catalog`, `[Priced]`, `[Not Priced]`, `[Zero Priced]`, `[Junk Price]`,
  `[Total Attrs]`, `[Priced %]`.
- Font-color each count column with its category color. On `[Priced %]` add **Data bars** with the
  rule-based color from DAX §5 (`<50%` red, `50–65%` amber, else green).

---

## 7. Page 2 — Attribute Detail  *(source: `AttributeDetail`)*

Now backed by the native per-catalog CSVs, so prices and I52 FP/TP/LP are available.

### 7.1 Category tab strip
- A **slicer** on `DimCategory[Category]`, **single-select**, **horizontal/tile** orientation; selected tile
  fill = the category color. Add per-tab counts with a small multi-row card, or use 4 bookmark buttons for
  the exact filled-pill look.

### 7.2 Search + export
- Add a **search-enabled slicer** on `AttributeDetail[AttributeCode]` (or use the table visual's built-in
  search). Place an **Export filtered list** button (the table "…" menu exports CSV).

### 7.3 The detail table
- **Table** columns in order: `Country`, `AttributeCode` (Attribute Value Code), `Modality Code`,
  `Base Price`, `Catalog`.
- **I52 FP/TP/LP:** add `FP`, `TP`, `LP` columns (accent blue `#3b82f6`). They'll be populated only for I52
  Priced rows and `null`/`—` elsewhere — that's expected. If you want them to appear *only* when the I52
  catalog is selected, drive a bookmark off the Catalog slicer to swap a wider table in.
- Mono font for code columns; render `Catalog` as a blue pill via conditional formatting
  (`#eef2ff` bg, `#4338ca` text).

### 7.4 Make it a real drill-through
Add `Country` and `Category` to this page's **Drill-through** filter well, so right-clicking a bar/KPI on the
Overview page → *Drill through → Attribute Detail* carries the context. (Both pages share the same dims,
so the filter flows cleanly.)

---

## 8. Page 3 — Quarterly Trend  *(source: `RunHistory`)*

First, a couple of helper columns on `RunHistory` (Data view → New column):
```DAX
QSort = RunHistory[Run_Year] * 10 + VALUE ( SUBSTITUTE ( RunHistory[Run_Quarter], "Q", "" ) )
QLabel = RunHistory[Run_Quarter] & " '" & RIGHT ( RunHistory[Run_Year], 2 )   // "Q2 '26"
```
Select `QLabel` → **Sort by column → QSort**.

### 8.1 Three KPI cards
- **Latest Priced %** (green) with ▲/▼ `pp` delta vs the prior quarter (from `RunHistory`).
- **Latest Not Priced %** (red) — "good" when it *drops*, so flip the color logic.
- **Avg Priced %** (brand blue `#4f86c6`) across all quarters. (All in DAX §3.)

### 8.2 Main combo — "Priced Coverage by Quarter"
- **Line and clustered column chart**: shared axis `QLabel`; column = `[Priced %]` (green `#2ECC71`, dark-green
  labels `#1e8449`); line = `[Not Priced %]` (red dashed `#E74C3C`).
- Optionally add a second line `[Priced %]` styled as a dark-green trend with a soft gradient area fill.
- Y-axis 0–100%, ticks 0/25/50/75/100, gridlines `#f3f4f6`.

### 8.3 Secondary — "Not Priced % — Trend Detail"
- **Area chart**: `QLabel` × `[Not Priced %]`, color `#E74C3C` gradient, Y-axis 0–50%.
- **Analytics → Constant line** at `0.18`, labeled "target ≤ 18%", dashed `#9ca3af`.

### 8.4 Note box
- Rectangle fill `#fff8e1`, 3px left border `#f6c343`, text `#6e4f00`: the classifier provenance note.

---

## 9. The Server (RF / HOS) toggle

The whole dataset swaps between servers. Two clean options:

**Option A — Slicer (simplest):** single-select slicer on `DimServer[Server]`, tile orientation, in the
header. Because every fact joins to `DimServer`, all pages filter at once.

**Option B — Bookmarks (exact look):** two header **Buttons** ("RF · Rightfit", "HOS"); two bookmarks that
set the `DimServer` selection and swap each button's on/off style; bind each button to its bookmark.

---

## 10. Refresh & publish

1. **File → Publish** to your Power BI workspace.
2. In the service: dataset → **Settings → Data source credentials** → sign in to **SharePoint (OAuth2 /
   organizational account)**.
3. **Scheduled refresh:** set it to run *after* your pipeline writes the CSVs (e.g. shortly after the
   quarterly script run). SharePoint cloud sources usually refresh without an on-prem gateway; if the files
   sit on a synced/on-prem location instead, install the **on-premises data gateway** and bind the source.
4. Because `dashboard_feed.csv` is overwritten (snapshot) and `run_history.csv` is appended (history), each
   refresh updates the Overview/Detail to the latest run while the Trend page grows over time — exactly the
   intended behavior.

---

## 11. Final polish checklist

- [ ] Cards: white fill, `#e5e7eb` border, **6px radius**, subtle shadow.
- [ ] Titles 13px Segoe UI Semibold `#1f2937`; subtitles 11px `#6b7280`.
- [ ] Category colors identical in every visual (donut, stacked, KPIs, matrix, table fonts).
- [ ] Tooltips on, dark style (`#1e2a3a`, white text).
- [ ] Visual headers off in view mode.
- [ ] Country/Catalog/Modality slicers cross-filter all visuals; Server slicer filters everything.
- [ ] Header/sidebar/filter bar copied onto all 3 pages.
- [ ] `N/A` modality/country either kept as a labeled slicer entry or hidden via a filter.

---

### Source-to-visual map (quick reference)

| Page element | Source table | Power BI visual |
|--------------|--------------|-----------------|
| KPI cards, donut, stacked, heat matrix, summary | `DashboardFeed` | new Card / Donut / Stacked column / Matrix / Table |
| Attribute detail list (+ prices, I52 FP/TP/LP) | `AttributeDetail` | Table + tile slicer / bookmarks |
| Quarterly trend (bars + line + area) | `RunHistory` | Line & clustered column / Area + constant line |
| Country / Catalog / Modality filters | `DimCountry/Catalog/Modality` | Slicers |
| Server RF/HOS toggle | `DimServer` | single-select slicer or bookmark buttons |
