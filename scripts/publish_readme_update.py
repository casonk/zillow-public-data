#!/usr/bin/env python3
"""Publish the README charts and data dates from the latest refresh as a pull request.

``refresh.py`` regenerates the ignored ``viz/`` and ``data/`` trees; the PNGs the
README embeds and its "Latest data" block only change when someone publishes
them. This script does that without touching the working checkout: it builds a
worktree of ``origin/main``, copies the curated charts from ``viz/``, rewrites
the block between the ``latest-data`` markers from the CSVs' newest dates, and,
if anything differs, pushes a branch and opens a pull request. Nothing changes
when the refresh brought no new data, so the weekly run is quiet.

    python3 scripts/publish_readme_update.py [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

START, END = "<!-- latest-data:start -->", "<!-- latest-data:end -->"
IMAGE = re.compile(r"!\[[^\]]*\]\(\./([^)/]+\.png)\)")
REFERENCE_DATASETS = (
    "zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
    "median_sale_price/Metro_median_sale_price_uc_sfrcondo_sm_month.csv",
    "invt_fs/City_invt_fs_uc_sfr_month.csv",
)
BRANCH = "automation/zillow-readme-refresh"
TITLE = "chore: refresh README charts and latest data dates"
BODY = (
    "Scheduled publish of the README charts and the latest-data block from the newest "
    "refresh. Only the curated root PNGs and README.md are touched."
)


class PublishError(RuntimeError):
    """A safe, user-facing failure."""


def curated_charts(readme: str) -> list[str]:
    """Root PNG names the README embeds (and refresh regenerates under viz/)."""
    seen: list[str] = []
    for name in IMAGE.findall(readme):
        if name not in seen:
            seen.append(name)
    return seen


def latest_block(latest: dict[str, str]) -> str:
    """The generated README block for the given dataset -> newest date mapping."""
    lines = [START, "", "| Dataset | Newest month |", "|---|---|"]
    for path in sorted(latest):
        lines.append(f"| `{path}` | {latest[path]} |")
    lines += ["", END]
    return "\n".join(lines)


def update_readme(readme: str, latest: dict[str, str]) -> str:
    """Replace the marked block, or add a "Latest data" section before "Directory layout"."""
    block = latest_block(latest)
    if START in readme and END in readme:
        before, rest = readme.split(START, 1)
        _, after = rest.split(END, 1)
        return before + block + after
    section = f"## Latest data\n\n{block}\n\n"
    marker = "## Directory layout"
    if marker in readme:
        return readme.replace(marker, section + marker, 1)
    return readme.rstrip("\n") + "\n\n" + section.rstrip("\n") + "\n"


def current_latest() -> dict[str, str]:
    import refresh  # needs pandas; imported lazily so the pure helpers stay light

    out = {}
    for path in REFERENCE_DATASETS:
        date = refresh.latest_date_for(path)
        if date:
            out[path] = date
    return out


def git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise PublishError(f"git {' '.join(args)}: {(result.stderr or result.stdout).strip()}")
    return result.stdout


def https_remote() -> str:
    url = git("remote", "get-url", "origin").strip()
    match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    if not match:
        raise PublishError(f"origin is not a GitHub remote: {url}")
    return f"https://github.com/{match.group(1)}.git"


def stage(worktree: Path, latest: dict[str, str]) -> list[str]:
    """Copy charts and rewrite the README in ``worktree``; return the changed files."""
    readme_path = worktree / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    changed: list[str] = []
    for name in curated_charts(readme):
        source = ROOT / "viz" / name
        target = worktree / name
        if source.is_file() and (
            not target.is_file() or source.read_bytes() != target.read_bytes()
        ):
            shutil.copyfile(source, target)
            changed.append(name)
    updated = update_readme(readme, latest)
    if updated != readme:
        readme_path.write_text(updated, encoding="utf-8")
        changed.append("README.md")
    return changed


def publish(dry_run: bool) -> int:
    helper = ["-c", "credential.helper=!gh auth git-credential"]
    remote = https_remote()
    git(*helper, "fetch", "-q", remote, "main:refs/remotes/origin/main")
    latest = current_latest()
    if not latest:
        raise PublishError("no reference datasets found under data/; run refresh.py first")
    with tempfile.TemporaryDirectory(prefix="zillow-publish-") as tmp:
        worktree = Path(tmp) / "wt"
        git("worktree", "add", "-q", "--detach", str(worktree), "origin/main")
        try:
            changed = stage(worktree, latest)
            if not changed:
                print("nothing to publish: charts and dates already match origin/main")
                return 0
            print("would publish:" if dry_run else "publishing:", ", ".join(changed))
            if dry_run:
                return 0
            existing = subprocess.run(
                ["gh", "pr", "list", "--head", BRANCH, "--state", "open", "--json", "number"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            ).stdout
            if existing.strip() not in {"", "[]"}:
                print(f"a pull request from {BRANCH} is already open; leaving it for review")
                return 0
            git("checkout", "-q", "-B", BRANCH, cwd=worktree)
            git("add", "--", *changed, cwd=worktree)
            git("commit", "-q", "-m", TITLE, cwd=worktree)
            git(*helper, "push", "-q", "-f", remote, f"{BRANCH}:{BRANCH}", cwd=worktree)
            result = subprocess.run(
                ["gh", "pr", "create", "--head", BRANCH, "--title", TITLE, "--body", BODY],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise PublishError((result.stderr or result.stdout).strip())
            print(result.stdout.strip())
            return 0
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=ROOT,
                capture_output=True,
                check=False,
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="Report what would change.")
    args = parser.parse_args(argv)
    try:
        return publish(args.dry_run)
    except PublishError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
