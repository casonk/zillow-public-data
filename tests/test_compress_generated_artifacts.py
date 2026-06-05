from pathlib import Path

from scripts.compress_generated_artifacts import (
    archive_path_for,
    compress_target,
    load_manifest,
    restore_target,
)


def write_sample_tree(root: Path) -> Path:
    data_dir = root / "data"
    nested = data_dir / "nested"
    nested.mkdir(parents=True)
    (data_dir / "sample.csv").write_text("RegionName,2026-01-31\nA,1\n", encoding="utf-8")
    (nested / "other.csv").write_text("RegionName,2026-02-28\nB,2\n", encoding="utf-8")
    return data_dir


def test_compress_prunes_and_restore_round_trips(tmp_path):
    data_dir = write_sample_tree(tmp_path)
    archive_dir = tmp_path / ".archives"

    result = compress_target(tmp_path, "data", archive_dir, prune_source=True)

    assert result.action == "compressed-and-pruned"
    assert not data_dir.exists()
    assert archive_path_for(archive_dir, "data").exists()

    manifest = load_manifest(archive_dir)
    assert manifest["archives"]["data"]["source_file_count"] == 2
    assert manifest["archives"]["data"]["source_size_bytes"] > 0

    restore_result = restore_target(tmp_path, "data", archive_dir)

    assert restore_result.action == "restored"
    assert (tmp_path / "data" / "sample.csv").read_text(encoding="utf-8").startswith("RegionName")
    assert (tmp_path / "data" / "nested" / "other.csv").exists()


def test_compress_skips_below_threshold(tmp_path):
    write_sample_tree(tmp_path)
    archive_dir = tmp_path / ".archives"

    result = compress_target(
        tmp_path,
        "data",
        archive_dir,
        min_size_bytes=10 * 1024 * 1024,
        prune_source=True,
    )

    assert result.action == "skip"
    assert "below threshold" in result.message
    assert (tmp_path / "data").exists()
    assert not archive_path_for(archive_dir, "data").exists()


def test_restore_skips_existing_source_without_overwrite(tmp_path):
    data_dir = write_sample_tree(tmp_path)
    archive_dir = tmp_path / ".archives"
    compress_target(tmp_path, "data", archive_dir)

    result = restore_target(tmp_path, "data", archive_dir)

    assert result.action == "skip"
    assert "source already exists" in result.message
    assert data_dir.exists()
