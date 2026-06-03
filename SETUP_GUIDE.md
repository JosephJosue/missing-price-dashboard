# Pricing Coverage Dashboard — Power BI Setup Guide

> See [`README.md`](README.md) for installation and how to run the pipeline.
> This guide covers only the Power BI / SharePoint setup.

## How the data is produced

Running `python main.py <SERVER>` (see the README) runs all five catalog
analyses and then `dashboard_export.py`, which reads every per-catalog output
CSV and produces two files in `Output/Dashboard/`:

| File | Purpose | Behavior |
|------|---------|----------|
| `dashboard_feed.csv` | Flat table powering all Power BI visuals (KPIs, charts, heat matrix, detail table) | **Overwritten** each run |
| `run_history.csv` | Aggregated counts per catalog/category/run date for the Quarterly Trend page | **Appended** each run |

The per-catalog analyses still produce their original-format CSVs in
`Output/I38/`, `Output/I51/`, etc. The download buttons in Power BI link
directly to these files so users get the native column format.

---

## Output Folder Structure (per server)

```
Output/
├── Dashboard/
│   ├── dashboard_feed.csv      ← Power BI main data source
│   └── run_history.csv         ← Power BI quarterly trend source
├── I38/
│   ├── I38_priced.csv          ← Original format (download)
│   ├── I38_not_priced.csv
│   ├── I38_zero_priced.csv
│   └── I38_junk_price.csv
├── I51/
│   └── ...
├── I52/
│   └── ...
├── I53/
│   └── ...
└── I62/
    └── ...
```

---

## Dashboard Feed Schema

| Column | Example | Description |
|--------|---------|-------------|
| Server | `HOS` | Which server the data was exported from |
| Catalog | `I38` | Which catalog file the attribute belongs to |
| Category | `Priced` | Classification: Priced / Not Priced / Price in 0 / Junk Price |
| Country | `BE` | Country code from the catalog |
| Attribute_Code | `CM_LIM58-8` | Attribute Value Code (or CVG Code for I62) |
| Modality_Code | `CT` | Modality Code (blank for I62) |
| Run_Date | `2026-05-28` | Date the script was executed |
| Run_Quarter | `Q2` | Quarter derived from run date |
| Run_Year | `2026` | Year derived from run date |

---

## Run History Schema

| Column | Example |
|--------|---------|
| Server | `HOS` |
| Run_Date | `2026-05-28` |
| Run_Quarter | `Q2` |
| Run_Year | `2026` |
| Catalog | `I38` |
| Category | `Priced` |
| Count | `935` |

---

## Power BI Setup Steps

### 1. Upload to SharePoint
After each script run, upload the entire `Output/` folder to SharePoint. Suggested structure:

```
SharePoint/Pricing Dashboard/
├── HOS/
│   ├── Dashboard/
│   │   ├── dashboard_feed.csv
│   │   └── run_history.csv
│   ├── I38/ ...
│   ├── I51/ ...
│   ├── I52/ ...
│   ├── I53/ ...
│   └── I62/ ...
└── RF/
    ├── Dashboard/
    │   ├── dashboard_feed.csv
    │   └── run_history.csv
    ├── I38/ ...
    └── ...
```

### 2. Connect Power BI to SharePoint

**Data sources to connect (4 total):**

1. `HOS/Dashboard/dashboard_feed.csv` → table name: `HOS_Feed`
2. `HOS/Dashboard/run_history.csv` → table name: `HOS_History`
3. `RF/Dashboard/dashboard_feed.csv` → table name: `RF_Feed`
4. `RF/Dashboard/run_history.csv` → table name: `RF_History`

In Power Query, append HOS_Feed and RF_Feed into a single `Dashboard_Feed` table (they have identical columns). Do the same for history files into `Run_History`.

### 3. Build the Visuals

**Page 1 — Overview (all powered by `Dashboard_Feed` table):**

- **Server toggle**: Slicer on `Server` column (single-select, buttons style)
- **Country slicer**: Slicer on `Country` column (dropdown, multi-select)
- **Catalog slicer**: Slicer on `Catalog` column (dropdown, multi-select)
- **Modality slicer**: Slicer on `Modality_Code` column (dropdown, multi-select)
- **KPI Cards**: 4 cards, each with a measure like:
  ```dax
  Priced_Count = CALCULATE(COUNTROWS(Dashboard_Feed), Dashboard_Feed[Category] = "Priced")
  Priced_Pct = DIVIDE([Priced_Count], COUNTROWS(Dashboard_Feed))
  ```
- **Donut chart**: Category on Legend, COUNTROWS on Values
- **Top 10 stacked bar**: Country on Axis, COUNTROWS on Values, Category on Legend. Add a Top N filter on Country by COUNTROWS = 10
- **Heat matrix**: Matrix visual with Country on Rows, Category on Columns, values = percentage of row total. Conditional formatting on cell background (green for Priced, red for Not Priced, etc.)
- **Summary table**: Table visual grouped by Country + Catalog, with measures for each category count + Priced %

**Page 2 — Detail / Drill-through (powered by `Dashboard_Feed`):**

- **Category selector**: Slicer on `Category` (single-select, buttons)
- **Detail table**: Table with Country, Attribute_Code, Modality_Code, Catalog columns
- **Download buttons**: For each catalog file, add a button that links to the SharePoint URL of the original CSV (e.g., `I38_not_priced.csv`). These preserve the original column format with all price fields.

**Page 3 — Quarterly Trend (powered by `Run_History` table):**

- **Clustered bar + line chart**: Run_Quarter + Run_Year on X-axis. Measures:
  ```dax
  Priced_Pct_Trend = 
  DIVIDE(
      CALCULATE(SUM(Run_History[Count]), Run_History[Category] = "Priced"),
      SUM(Run_History[Count])
  )
  ```
- Slicers for Country and Catalog should cross-filter (note: Run_History is aggregated, so country-level filtering requires the detail feed or a separate history table)

### 4. Refresh Schedule
After each script run (2× per quarter), upload the new files to SharePoint and hit Refresh in Power BI. If using Power BI Gateway + SharePoint connector, you can set up scheduled refresh.

---

## Workflow Summary

```
1. Get master data files from RF / HOS servers
2. Run  python main.py RF   (or  python main.py HOS,  or  python main.py all)
   ├── Runs I38, I51, I52, I53, I62 analyses  →  original CSVs
   └── Runs dashboard_export                  →  dashboard_feed.csv + run_history.csv
3. Upload Output/ folder to SharePoint
4. Refresh Power BI dashboard
```
