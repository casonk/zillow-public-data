# LESSONSLEARNED.md

Tracked durable lessons for `zillow-public-data`.
Unlike `CHATHISTORY.md`, this file should keep only reusable lessons that should change how future sessions work in this repo.

## How To Use

- Read this file after `AGENTS.md` and before `CHATHISTORY.md` when resuming work.
- Add lessons that generalize beyond a single session.
- Keep entries concise and action-oriented.
- Do not use this file for transient status updates or full session logs.

## Lessons

- Document the repository around its real execution, curation, or integration flow instead of only the top-level folder list.
- Keep local-only, private, reference-only, or generated boundaries explicit so published or runtime behavior is not confused with offline material or non-committable inputs.
- Re-run repo-appropriate validation after changing generated artifacts, diagrams, workflows, or other CI-facing files so formatting and compatibility issues are caught before push.

### 2026-03-27 — Keep the automatic refresh pipeline separate from the manual README publish step

- `refresh.py` owns catalog expansion, CSV download, validation, plot generation,
  and freshness reporting.
- The repo-root README PNGs are curated publish artifacts copied from `viz/`
  only when an operator intends to refresh the public examples.
- Architecture docs and diagrams should not imply that `refresh.py`
  automatically overwrites those tracked root PNGs.
