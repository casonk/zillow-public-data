# AGENTS.md

## Project Purpose

This repo mirrors Zillow public CSV datasets locally and republishes a small set
of example charts that are referenced from the README.

## Repo Layout

- `doc_urls.pickle`: cached Zillow dataset path map used to build download URLs.
- `refresh.py`: canonical batch workflow for downloading data and regenerating
  plots.
- `data/`: full downloaded Zillow CSV corpus. Generated output, large, and kept
  out of git.
- `viz/`: full regenerated plot set. Generated output, kept out of git.
- Root `*.png`: curated sample charts that should stay in sync with the latest
  analytics run because the README embeds them directly.

## Working Rules

- Prefer `python refresh.py --resume` over the notebooks for refresh work.
- Use `python refresh.py --skip-download` when only the plots need to be rerun.
- Expect many 404s. Zillow does not publish every dataset for every geography.
- Do not commit `data/` or `viz/` unless the user explicitly asks for large
  generated artifacts and confirms the storage plan.
- When publishing a refresh, update the tracked root PNGs from `viz/` so the
  README examples reflect the current data.

## Validation

1. Run `python refresh.py --resume`.
2. Confirm the `[summary]` and `[latest]` lines look sane.
3. If the refresh is meant to be published, copy the five tracked root PNGs from
   `viz/` and verify the README still points at those filenames.
