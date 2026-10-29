# Changelog

All notable changes to `zillow-public-data` are documented here.

## Unreleased

- Add `scripts/publish_readme_update.py`: after each refresh it copies the README's
  curated charts from `viz/`, rewrites a new "Latest data" block from the newest
  CSV dates, and opens a pull request when they changed. The scheduled job reported
  success while the committed charts stayed at the March 2026 versions because the
  publish step was manual.
- Add the `Private :: Do Not Upload` classifier so PyPI rejects an upload of this
  distribution; the repository is not published as a package.

- Added the portfolio-standard governance, continuity, and contributor baseline files.
