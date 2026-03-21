# Contributor Architecture

This document traces the download → validation → visualization path that
`refresh.py` implements. The idea mirrors the style used in
`personal-finance/docs/contributor-architecture-blueprint.md`: small, focused
sections that explain what each layer owns and how an engineer can extend it.

## Key Components

- `doc_urls.pickle`: cached mapping from dataset descriptions to Zillow CSV
  file paths. Each path includes a geography token (`Metro`, `State`, etc.) so
  the script can re-stitch every supported geography without hard-coding URLs.
- `refresh.py`: the central workflow. It:
  1. iterates the candidate CSV paths derived from `doc_urls.pickle`,
  2. downloads them from `files.zillowstatic.com` (with a mirror fallback),
  3. validates each CSV (non-empty, UTF-8/Latin-1), and
  4. regenerates the plots in `./viz/`, skipping tables with no numeric data.
- `data/`: final download output grouped by topic (`zhvi/`, `median_sale_price/`,
  `invt_fs/`, etc.).
- `viz/`: every generated PNG, one per dataset/geography (used to update the
  tracked README images).
- Root PNGs: curated visuals mentioned in this README so the homepage reflects
  the latest data.

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
5. The tracked root PNGs in the README are overwritten at the end of the run so
   visitors always see samples generated from the current CSV corpus.

## Operations

- Use `python refresh.py --resume` for day-to-day refresh work; it keeps partial
  downloads intact while filling in new files.
- Use `python refresh.py --skip-download` when you only need plot updates (this
  is fast because it skips the large downloads).
- Rerun `python refresh.py --skip-download --skip-viz` if you want to verify the
  latest `data/` contents without touching either downloads or plots, e.g.,
  after manual edits.
- The README images, `AGENTS.md`, and `docs/ARCHITECTURE.md` together document
  the workflow so future contributors can see how the pieces fit.
