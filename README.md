# zillow-public-data
This repository mirrors Zillow’s public CSV feeds (no API key required) and
rebuilds a few example charts so the README can illustrate how the
timeseries evolve.

## Data Sources

- **Dataset catalog & downloads:** <https://www.zillow.com/research/data/>
- **Developer API reference:** <https://www.zillowgroup.com/developers/api/public-data/real-estate-metrics/>
- **ZHVI methodology:** <https://www.zillow.com/research/methodology-neural-zhvi-32128/>
- **ZORI methodology:** <https://www.zillow.com/research/zori-repeat-rent-methodology-27092/>
- **Market Heat Index methodology:** <https://www.zillow.com/research/market-heat-index-methodology-31867/>

All data is free for public use with attribution to Zillow per their [Terms of Use](https://www.zillow.com/z/corp/terms/).

## Overview

- `doc_urls.pickle` contains the current set of Zillow endpoints plus example
  geographies so the refresh workflow knows which CSVs to request.
- `refresh.py` is the canonical operator entrypoint. It loads the catalog,
  expands geography-specific candidate paths, downloads or resumes CSVs into
  `data/`, regenerates the full chart corpus into `viz/`, and reports the
  newest available month for a few reference datasets.
- `data/` holds the downloaded CSV corpus; `viz/` contains the full regenerated
  chart set, while the README keeps a curated subset of those PNGs checked in
  at the repo root for publication.
- `tests/test_refresh.py` is the lightweight regression surface for catalog
  loading, geography expansion, and date-column detection.
- See `docs/ARCHITECTURE.md` for a concise diagram and description of the
  download → plot workflow.

## Running the refresh

1. `python refresh.py --resume` downloads any missing CSVs while reusing what’s
   already in `./data/`.
2. `python refresh.py --skip-download` regenerates every chart from the current
   `./data/` corpus (use after manually editing CSVs or when you just want new
   proofs without re-downloading).
3. Both commands print `[summary]` and `[latest]` lines so you can confirm the
   run touched all expected datasets and see the newest date in each reference
   CSV.

The helper script already handles partial downloads, Latin-1 encoded CSVs, and
non-numeric rows so rerunning `refresh.py` is the preferred way to keep the repo
in sync. Use `python refresh.py --skip-viz` only when you need to verify the data
download step without generating any charts.

## Generated artifact compression

`data/` and `viz/` can be archived locally when they are taking too much disk
space. Archives live under ignored `.zillow-generated-archives/` and can be
restored before the next refresh.

```bash
python scripts/compress_generated_artifacts.py status
python scripts/compress_generated_artifacts.py auto
python scripts/compress_generated_artifacts.py restore --targets data viz
```

`auto` compresses targets at or above `250 MiB` and removes the uncompressed
directory only after the archive has been verified. Use `--keep-source` to keep
the original directories, or `--force` after a new refresh when an existing
archive should be replaced.

## Visual preview

These PNGs are published in the README as examples. `refresh.py` regenerates the
full `./viz/` corpus, then a publish-intended refresh manually copies the
curated subset below from `viz/` to the repo root:

![City_invt_fs_uc_sfr_month.csv.png](./City_invt_fs_uc_sfr_month.csv.png)
![County_mean_doz_pending_uc_sfrcondo_sm_month.csv.png](./County_mean_doz_pending_uc_sfrcondo_sm_month.csv.png)
![Metro_median_sale_price_uc_sfrcondo_sm_month.csv.png](./Metro_median_sale_price_uc_sfrcondo_sm_month.csv.png)
![Neighborhood_zhvi_uc_sfrcondo_tier_0.67_1.0_sm_sa_month.csv.png](./Neighborhood_zhvi_uc_sfrcondo_tier_0.67_1.0_sm_sa_month.csv.png)
![State_mean_sale_price_uc_sfrcondo_month.csv.png](./State_mean_sale_price_uc_sfrcondo_month.csv.png)

## Directory layout

- `refresh.py`: orchestrates the full flow (catalog load + candidate expansion +
  download + viz generation + freshness summaries).
- `doc_urls.pickle`: Zillow endpoint map used by `refresh.py`.
- `data/`: large downloaded CSVs (`zhvi/`, `median_sale_price/`, etc.).
- `viz/`: generated charts for all region/dataset combinations.
- `scripts/compress_generated_artifacts.py`: reversible local archiver for the
  ignored generated `data/` and `viz/` directories.
- Root PNGs: curated subset manually published from `viz/` for the README.
- `tests/test_refresh.py`: offline checks around `load_doc_urls`,
  `iter_candidate_paths`, and date-column discovery.
- `docs/ARCHITECTURE.md`: high-level architecture sketch describing how the
  inputs move through `refresh.py` and where the manual publish step begins.

## Troubleshooting

- If Zillow adds/removes CSVs, rerun `python refresh.py --resume` so the script can
  skip missing geographies and record what was unavailable.
- If `refresh.py` errors while reading a CSV, the logs now try Latin-1 as a
  fallback and skip non-numeric outputs automatically.
- When the README pixels still look stale, rerun `python refresh.py --skip-download`
  so `viz/` is rebuilt from the current `data/`, then manually copy the curated
  PNGs you want to publish from `viz/` to the repo root.

## Tests

- `pytest tests/test_refresh.py` validates the helper utilities used by
  `refresh.py` (doc map loading, candidate path expansion, date column discovery)
  without making network calls. Run this after touching `refresh.py` or
  `doc_urls.pickle` before pushing.
