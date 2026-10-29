"""Offline checks for the README publish helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_readme_update.py"
SPEC = importlib.util.spec_from_file_location("publish_readme_update", SCRIPT)
pub = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pub)

README = (
    "# t\n\n![a](./A.png)\n![b](./B.csv.png)\n![a again](./A.png)\n"
    "![remote](https://x.example/C.png)\n\n## Directory layout\n\n- x\n"
)
LATEST = {"zhvi/Metro.csv": "2026-09-30", "invt_fs/City.csv": "2026-09-30"}


def test_curated_charts_are_the_local_root_pngs_once():
    assert pub.curated_charts(README) == ["A.png", "B.csv.png"]


def test_block_is_sorted_and_marked():
    block = pub.latest_block(LATEST)
    assert block.startswith(pub.START) and block.endswith(pub.END)
    assert block.index("invt_fs") < block.index("zhvi")


def test_first_update_adds_a_section_before_directory_layout():
    out = pub.update_readme(README, LATEST)
    assert out.index("## Latest data") < out.index("## Directory layout")
    assert "| `zhvi/Metro.csv` | 2026-09-30 |" in out


def test_update_is_idempotent_and_replaces_in_place():
    once = pub.update_readme(README, LATEST)
    assert pub.update_readme(once, LATEST) == once
    newer = pub.update_readme(once, {**LATEST, "zhvi/Metro.csv": "2026-10-31"})
    assert "2026-10-31" in newer and newer.count(pub.START) == 1


def test_stage_copies_only_changed_charts_and_rewrites_readme(tmp_path, monkeypatch):
    root, worktree = tmp_path / "root", tmp_path / "wt"
    (root / "viz").mkdir(parents=True)
    worktree.mkdir()
    (worktree / "README.md").write_text(README)
    (worktree / "A.png").write_bytes(b"old")
    (worktree / "B.csv.png").write_bytes(b"same")
    (root / "viz" / "A.png").write_bytes(b"new")
    (root / "viz" / "B.csv.png").write_bytes(b"same")
    monkeypatch.setattr(pub, "ROOT", root)
    changed = pub.stage(worktree, LATEST)
    assert changed == ["A.png", "README.md"]
    assert (worktree / "A.png").read_bytes() == b"new"
    assert pub.stage(worktree, LATEST) == []
