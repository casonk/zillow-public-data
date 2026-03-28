# Contributor Architecture Blueprint

This document is a concise map of how `zillow-public-data` expands the Zillow
catalog, refreshes downloaded datasets, regenerates the full chart corpus, and
then optionally publishes a curated subset to the README.

## High-Level Layers

1. Catalog expansion layer (`doc_urls.pickle`, `load_doc_urls`, `iter_candidate_paths`)
   - Cached Zillow dataset-path metadata is loaded from `doc_urls.pickle`.
   - `iter_candidate_paths` expands each metro-oriented path across the supported
     geographies so the downloader can try the full public corpus without
     hard-coding every URL.
2. Download and validation layer (`download_all`, `is_non_empty_csv`, `data/`)
   - `download_all` walks the candidate list against Zillow's `public_csvs` and
     `public_v2` mirrors.
   - Empty CSVs are deleted immediately, while `--resume` preserves already-valid
     files inside `data/`.
3. Plot generation layer (`plot_all`, `make_selections`, `date_columns`, `viz/`)
   - `plot_all` reads the downloaded CSV corpus, filters each geography to the
     configured reference regions, and writes the full PNG set to `viz/`.
   - Date-column detection and numeric coercion determine whether a dataset is
     plottable.
4. Reporting and publish layer (`latest_date_for`, README PNGs)
   - `refresh.py` prints `[summary]` and `[latest]` lines so the operator can
     confirm coverage and freshness after a run.
   - The tracked root PNGs used by `README.md` are a manual publish step copied
     from `viz/` only when new examples are intentionally being published.
5. Test and documentation layer (`tests/test_refresh.py`, `docs/`)
   - `tests/test_refresh.py` keeps the candidate-expansion and date-detection
     helpers stable without making network calls.
   - `docs/ARCHITECTURE.md` and `docs/diagrams/` should describe the same
     runtime pipeline and manual publish boundary.

## Key Entry Points

- `python refresh.py --resume`
- `python refresh.py --skip-download`
- `pytest tests/test_refresh.py`
- tracked root `*.png` files referenced by `README.md`
- `.github/workflows/ci.yml`

## Validation

```bash
pytest tests/test_refresh.py
python refresh.py --resume
python refresh.py --skip-download
```

After a publish-intended refresh, confirm the tracked root PNGs still match the
current README references and were deliberately copied from `viz/`.
