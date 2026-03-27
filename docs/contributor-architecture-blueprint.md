# Contributor Architecture Blueprint

This document is a concise map of how `zillow-public-data` refreshes downloaded datasets and republishes curated charts.

## High-Level Layers

1. Dataset catalog layer (`doc_urls.pickle`)
   - Cached Zillow dataset-path metadata is used to build refresh targets.
   - URL-map changes affect what the refresh pipeline can discover and download.
2. Refresh workflow layer (`refresh.py`)
   - The canonical batch workflow downloads datasets and regenerates charts.
   - `--resume` is the safe default because Zillow publishes an uneven set of files and many requests can 404.
3. Generated artifact layer (`data/`, `viz/`)
   - Full datasets and full visualization output stay local and out of git.
   - Publication changes should update only the curated tracked root PNGs when necessary.
4. Documentation layer (`README.md`, tracked root PNGs)
   - The README embeds a small set of representative charts.
   - Those tracked images must stay aligned with the latest intended published refresh.

## Key Entry Points

- `python refresh.py --resume`
- `python refresh.py --skip-download`
- tracked root `*.png` files referenced by `README.md`
- `.github/workflows/ci.yml`

## Validation

```bash
python refresh.py --resume
python refresh.py --skip-download
```

After a publish-intended refresh, confirm the tracked root PNGs still match the current README references.
