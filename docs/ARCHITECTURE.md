# Contributor Architecture

This document traces the real download → validation → visualization pipeline
implemented by `refresh.py`, then separates that runtime path from the manual
publish step used for the README preview PNGs.

## Visual diagrams

- `docs/diagrams/architecture.puml`: PlantUML source for the core workflow. Run
  `plantuml docs/diagrams/architecture.puml` to regenerate PNG/SVG renders when
  the data-flow changes.
- `docs/diagrams/architecture.drawio`: Draw.io project (zipped XML). Open it in
  `https://app.diagrams.net` or `drawio` desktop to make tweaks, and export
  artwork as needed for other documentation.
- `docs/diagrams/repo-architecture.puml` and
  `docs/diagrams/repo-architecture.drawio`: portfolio-standard architecture
  sources kept in sync with the same workflow.

With both sources in place, contributors can edit whichever tool they prefer
and use the matching renderer to keep the pictures aligned with the text.

## Key Components

- `doc_urls.pickle`: cached mapping from dataset descriptions to Zillow CSV
  file paths. Each path includes a geography token (`Metro`, `State`, etc.) so
  the script can re-stitch every supported geography without hard-coding URLs.
- `refresh.py`: the central workflow. It:
  1. parses operator flags and ensures `data/` / `viz/` exist,
  2. loads `doc_urls.pickle` and expands geography-specific candidates through
     `iter_candidate_paths`,
  3. downloads CSVs from Zillow's `public_csvs` / `public_v2` mirrors through
     `download_all`,
  4. deletes empty CSVs and keeps resume-safe files through `is_non_empty_csv`,
  5. regenerates plots through `plot_all`, `make_selections`, and
     `date_columns`, and
  6. reports sample freshness with `latest_date_for`.
- `data/`: final download output grouped by topic (`zhvi/`, `median_sale_price/`,
  `invt_fs/`, etc.).
- `viz/`: every generated PNG, one per dataset/geography. This is the full local
  render corpus.
- `.zillow-generated-archives/`: local-only `tar.gz` archives for compressed
  copies of ignored generated output. The archive helper verifies archives
  before pruning the uncompressed `data/` or `viz/` directory.
- `scripts/compress_generated_artifacts.py`: operational helper for checking,
  compressing, pruning, and restoring the ignored generated output directories.
- Root PNGs: curated README visuals copied from `viz/` only when an operator is
  intentionally publishing new examples.
- `tests/test_refresh.py`: fast offline checks for catalog loading, candidate
  expansion, and date-column detection.

## Data Flow

1. `refresh.py --resume` builds the canonical candidate list from
   `doc_urls.pickle`. When `--resume` is set, previously downloaded, non-empty
   CSVs are skipped so the run can recover from interruptions.
2. Every candidate is fetched against Zillow’s `public_csvs` and `public_v2`
   mirrors, timestamped to avoid stale caches.
3. After writing a CSV, the script ensures it contains data; empty CSVs are
   deleted and recorded as such.
4. Once the download pass finishes (or when `--skip-download` is used), the
   script regenerates all plots from `./data/`. Each chart is filtered to the
   configured region list (Metro, ZIP, City, etc.), numeric columns are
   coerced, and rows/columns that remain empty are dropped before plotting.
5. The command prints `[summary]` counters plus a few `[latest]` timestamps so
   the operator can verify what was refreshed.
6. If the refresh is meant to update the README, the operator manually copies a
   curated subset of PNGs from `viz/` to the repo root after reviewing them.

## Operations

- Use `python refresh.py --resume` for day-to-day refresh work; it keeps partial
  downloads intact while filling in new files.
- Use `python refresh.py --skip-download` when you only need plot updates (this
  is fast because it skips the large downloads).
- Rerun `python refresh.py --skip-download --skip-viz` if you want to verify the
  latest `data/` contents without touching either downloads or plots, e.g.,
  after manual edits.
- Use `python scripts/compress_generated_artifacts.py auto` to reclaim local
  disk from generated `data/` and `viz/` outputs. Restore with
  `python scripts/compress_generated_artifacts.py restore --targets data viz`
  before refresh work if those directories were pruned.
- Run `pytest tests/test_refresh.py` after changing the catalog-expansion or
  date-detection logic.
- The README images, `AGENTS.md`, `docs/ARCHITECTURE.md`, and the standard
  `repo-architecture.*` diagrams should all continue to describe the same split
  between the automatic pipeline and the manual README publish step.
