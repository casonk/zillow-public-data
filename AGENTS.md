# AGENTS.md

## Project Purpose

This repo mirrors Zillow public CSV datasets locally and republishes a small set
of example charts that are referenced from the README.

## Reference URLs

- **Dataset catalog & downloads:** <https://www.zillow.com/research/data/>
- **Developer API reference:** <https://www.zillowgroup.com/developers/api/public-data/real-estate-metrics/>
- **ZHVI methodology:** <https://www.zillow.com/research/methodology-neural-zhvi-32128/>
- **ZORI methodology:** <https://www.zillow.com/research/zori-repeat-rent-methodology-27092/>
- **Market Heat Index methodology:** <https://www.zillow.com/research/market-heat-index-methodology-31867/>

## Repo Layout

- `doc_urls.pickle`: cached Zillow dataset path map used to build download URLs.
- `refresh.py`: canonical batch workflow for catalog expansion, download,
  validation, plot generation, and freshness reporting.
- `data/`: full downloaded Zillow CSV corpus. Generated output, large, and kept
  out of git.
- `viz/`: full regenerated plot set. Generated output, kept out of git.
- `.zillow-generated-archives/`: local-only compressed archives of `data/` and
  `viz/` created by `scripts/compress_generated_artifacts.py`; ignored by git.
- Root `*.png`: curated sample charts that should stay in sync with the latest
  published refresh because the README embeds them directly.

## Working Rules

- Prefer `python refresh.py --resume` over the notebooks for refresh work.
- Use `python refresh.py --skip-download` when only the plots need to be rerun.
- Expect many 404s. Zillow does not publish every dataset for every geography.
- Do not commit `data/` or `viz/` unless the user explicitly asks for large
  generated artifacts and confirms the storage plan.
- Treat the tracked root PNGs as a manual publish step. `refresh.py` regenerates
  `viz/`, then an operator copies the curated README examples from `viz/` to the
  repo root when publishing a refresh.
- Use `python scripts/compress_generated_artifacts.py auto` to compress the
  ignored generated `data/` and `viz/` directories when local disk pressure
  matters. Use `restore --targets data viz` before refresh work if the
  uncompressed directories have been pruned.
- Keep `docs/ARCHITECTURE.md` and `docs/diagrams/` explicit about that boundary:
  the automated pipeline stops at `viz/`.

## Validation

1. Run `pytest tests/test_refresh.py` after changing catalog, candidate-path, or
   date-column logic.
2. Run `pytest tests/test_compress_generated_artifacts.py` after changing local
   archive/compression behavior.
3. Run `python refresh.py --resume`.
4. Confirm the `[summary]` and `[latest]` lines look sane.
5. If the refresh is meant to be published, copy the five tracked root PNGs from
   `viz/` and verify the README still points at those filenames.

## Sudo Boundary

Agents will never be able to run `sudo` commands in this environment. If a task requires elevated system changes, make the repo edits and run the validation that can be done without `sudo`, then give the user the exact command(s) to run.

Always require the user to run those commands instead of retrying `sudo`; do not claim a sudo-backed live change was applied until the user shares the result.

## Local CI Verification

Run before every push:

```bash
pre-commit run --all-files
pytest -q
```

Do not push changes that have not passed all checks locally.

## Portfolio Standards Reference

For portfolio-wide repository standards and baseline conventions, consult the control-plane repo at `./util-repos/traction-control` from the portfolio root.

Start with:
- `./util-repos/traction-control/AGENTS.md`
- `./util-repos/traction-control/README.md`
- `./util-repos/traction-control/LESSONSLEARNED.md`

Shared implementation repos available portfolio-wide:
- `./util-repos/archility` for architecture toolchain bootstrap/render orchestration, Graphviz-capable diagram support, deterministic starter scaffolding, agentic architecture authoring, and architecture-documentation drift checks
- `./util-repos/auto-pass` for KeePassXC-backed password management and secret retrieval/update flows
- `./util-repos/nordility` for NordVPN-based VPN switching and connection orchestration
- `./util-repos/shock-relay` for external messaging across supported providers such as Signal, Telegram, Twilio SMS, WhatsApp, and Gmail IMAP
- `./util-repos/snowbridge` for SMB-based private file sharing and phone-accessible fileshare workflows
- `./util-repos/dyno-lab` for unified test bench utilities — fixtures, subprocess/HTTP/env mocks, schema validation, smoke scaffolding, and pytest markers/fixtures
- `./util-repos/short-circuit` for WireGuard VPN setup and configuration, establishing private tunnels with SMB, HTTPS, and SSH access

When another repo needs architecture toolchain bootstrap/rendering, architecture inventory/scaffolding, password management, VPN switching, or external messaging, prefer integrating with these repos instead of re-implementing the capability locally.

## Agent Memory

Use `./LESSONSLEARNED.md` as the tracked durable lessons file for this repo.
Use `./CHATHISTORY.md` as the standard local handoff file for this repo.

- `LESSONSLEARNED.md` is tracked and should capture only reusable lessons.
- `CHATHISTORY.md` is local-only, gitignored, and should capture transient handoff context.
- Read `LESSONSLEARNED.md` and `CHATHISTORY.md` after `AGENTS.md` when resuming work.
- Add durable lessons to `LESSONSLEARNED.md` when they should influence future sessions.
- Keep transient entries concise and focused on refresh status, generated artifacts, blockers, and next steps.
