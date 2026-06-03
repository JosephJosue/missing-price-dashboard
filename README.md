# Missing-Price Dashboard Pipeline

Classifies attribute pricing coverage across five catalogs (I38, I51, I52, I53,
I62) for each server (HOS, RF) and produces a consolidated feed for a Power BI
dashboard.

For every catalog each attribute is sorted into one of four buckets:

| Bucket | Meaning |
|--------|---------|
| `priced` | a valid, non-zero price exists |
| `not_priced` | price is missing |
| `zero_priced` | price is present but zero |
| `junk_price` | a price exists for an attribute not in the master list |

## Project layout

| File | Responsibility |
|------|----------------|
| `config.py` | Resolves all input/output paths from `PRICING_BASE_DIR` |
| `common.py` | Shared I/O helpers + the generic price-classification engine |
| `catalogs.py` | The five per-catalog analyses (`run_i38` … `run_i62`) |
| `dashboard_export.py` | Consolidates the per-catalog CSVs into the Power BI feed |
| `main.py` | Pipeline entry point (replaces the old `Master_run_*.py`) |
| `SETUP_GUIDE.md` | Power BI / SharePoint setup instructions |

The codebase uses plain composable functions grouped into focused modules — no
classes — so the classification logic lives in exactly one place and the
per-server/per-catalog scripts are no longer copy-pasted.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Point the pipeline at your data folder (no paths are hardcoded):
   ```bash
   # macOS / Linux
   export PRICING_BASE_DIR="$HOME/PST Activities - No & Zero Pricing"

   # Windows (PowerShell)
   setx PRICING_BASE_DIR "C:\Users\<you>\Philips\PST Activities - No & Zero Pricing"
   ```

   Expected layout under that folder:
   ```
   <PRICING_BASE_DIR>/<SERVER>/
       I files/   ← input I-catalog spreadsheets (.xlsx)
       B files/   ← input B-reference spreadsheets (.xlsx)
       Output/    ← generated CSVs (created automatically)
   ```

## Usage

```bash
python main.py HOS                       # one server
python main.py all                       # every server
python main.py RF --country IN US        # optional filters
python main.py HOS --modality CT MR
```

Each run writes the per-catalog CSVs under `Output/<Ixx>/`, the Power BI files
under `Output/Dashboard/`, and a log to `Output/run_log_<server>.txt`.

To rebuild only the dashboard feed from existing CSVs:

```bash
python dashboard_export.py "<...>/HOS/Output" HOS
```
