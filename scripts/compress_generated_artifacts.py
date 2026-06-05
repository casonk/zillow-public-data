#!/usr/bin/env python3
"""Archive and restore ignored Zillow refresh outputs.

The repository keeps the large generated ``data/`` and ``viz/`` directories out
of git. This utility gives operators and automation a reversible way to compress
those directories when local disk pressure matters.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE_DIR = ".zillow-generated-archives"
DEFAULT_TARGETS = ("data", "viz")
MANIFEST_NAME = "manifest.json"
MIB = 1024 * 1024


class ArchiveError(RuntimeError):
    """Raised when archiving or restoring would be unsafe."""


@dataclass(frozen=True)
class TreeStats:
    path: Path
    exists: bool
    file_count: int = 0
    total_bytes: int = 0
    latest_mtime_ns: int = 0


@dataclass(frozen=True)
class ActionResult:
    target: str
    action: str
    message: str
    archive_path: Path | None = None
    source_bytes: int = 0
    archive_bytes: int = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def format_mib(byte_count: int) -> str:
    return f"{byte_count / MIB:.1f} MiB"


def resolve_archive_dir(root: Path, archive_dir: str | Path) -> Path:
    archive_path = Path(archive_dir)
    if not archive_path.is_absolute():
        archive_path = root / archive_path
    return archive_path


def validate_target_name(target: str) -> str:
    if target not in DEFAULT_TARGETS:
        allowed = ", ".join(DEFAULT_TARGETS)
        raise ArchiveError(f"unsupported target {target!r}; expected one of: {allowed}")
    return target


def collect_tree_stats(path: Path) -> TreeStats:
    if not path.exists():
        return TreeStats(path=path, exists=False)
    if path.is_symlink():
        raise ArchiveError(f"refusing to archive symlinked path: {path}")
    if not path.is_dir():
        raise ArchiveError(f"refusing to archive non-directory path: {path}")

    file_count = 0
    total_bytes = 0
    latest_mtime_ns = path.stat().st_mtime_ns
    for entry in path.rglob("*"):
        if entry.is_symlink():
            raise ArchiveError(f"refusing to archive symlink inside generated output: {entry}")
        if not entry.is_file():
            continue
        stat = entry.stat()
        file_count += 1
        total_bytes += stat.st_size
        latest_mtime_ns = max(latest_mtime_ns, stat.st_mtime_ns)

    return TreeStats(
        path=path,
        exists=True,
        file_count=file_count,
        total_bytes=total_bytes,
        latest_mtime_ns=latest_mtime_ns,
    )


def archive_path_for(archive_dir: Path, target: str) -> Path:
    return archive_dir / f"{target}.tar.gz"


def manifest_path_for(archive_dir: Path) -> Path:
    return archive_dir / MANIFEST_NAME


def load_manifest(archive_dir: Path) -> dict[str, Any]:
    path = manifest_path_for(archive_dir)
    if not path.exists():
        return {"version": 1, "archives": {}}
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if "archives" not in manifest:
        manifest["archives"] = {}
    return manifest


def write_manifest(archive_dir: Path, manifest: dict[str, Any]) -> None:
    path = manifest_path_for(archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{MANIFEST_NAME}.", suffix=".tmp", dir=archive_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
        Path(temp_name).replace(path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def validate_archive_member(member_name: str, expected_root: str) -> None:
    member_path = PurePosixPath(member_name)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise ArchiveError(f"unsafe archive member path: {member_name}")
    if not member_path.parts or member_path.parts[0] != expected_root:
        raise ArchiveError(
            f"archive member {member_name!r} is outside expected root {expected_root!r}"
        )


def verify_archive(archive_path: Path, target: str, expected_file_count: int) -> int:
    with tarfile.open(archive_path, "r:*") as archive:
        members = archive.getmembers()
        for member in members:
            validate_archive_member(member.name, target)
        archive_file_count = sum(1 for member in members if member.isfile())

    if archive_file_count != expected_file_count:
        raise ArchiveError(
            f"{archive_path} contains {archive_file_count} files; expected {expected_file_count}"
        )
    return archive_file_count


def update_manifest_entry(
    archive_dir: Path,
    target: str,
    source_stats: TreeStats,
    archive_path: Path,
) -> None:
    manifest = load_manifest(archive_dir)
    manifest["archives"][target] = {
        "archive": archive_path.name,
        "created_at": utc_now(),
        "format": "tar.gz",
        "source_file_count": source_stats.file_count,
        "source_latest_mtime_ns": source_stats.latest_mtime_ns,
        "source_size_bytes": source_stats.total_bytes,
        "target": target,
    }
    write_manifest(archive_dir, manifest)


def compress_target(
    root: Path,
    target: str,
    archive_dir: Path,
    *,
    min_size_bytes: int = 0,
    prune_source: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> ActionResult:
    target = validate_target_name(target)
    source_path = root / target
    source_stats = collect_tree_stats(source_path)
    archive_path = archive_path_for(archive_dir, target)

    if not source_stats.exists:
        if archive_path.exists():
            return ActionResult(
                target, "skip", "source missing; archive already exists", archive_path
            )
        return ActionResult(target, "skip", "source missing", archive_path)

    if source_stats.total_bytes < min_size_bytes:
        return ActionResult(
            target,
            "skip",
            f"source is {format_mib(source_stats.total_bytes)}, below threshold",
            archive_path,
            source_bytes=source_stats.total_bytes,
        )

    if archive_path.exists() and not force:
        return ActionResult(
            target,
            "skip",
            "archive already exists; use --force to replace it",
            archive_path,
            source_bytes=source_stats.total_bytes,
            archive_bytes=archive_path.stat().st_size,
        )

    if dry_run:
        action = "would-compress-and-prune" if prune_source else "would-compress"
        return ActionResult(
            target,
            action,
            f"would archive {source_stats.file_count} files ({format_mib(source_stats.total_bytes)})",
            archive_path,
            source_bytes=source_stats.total_bytes,
        )

    archive_dir.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target}.", suffix=".tar.gz.tmp", dir=archive_dir)
    os.close(fd)
    temp_path = Path(temp_name)

    try:
        with tarfile.open(temp_path, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            archive.add(source_path, arcname=target, recursive=True)
        verify_archive(temp_path, target, source_stats.file_count)
        temp_path.replace(archive_path)
        update_manifest_entry(archive_dir, target, source_stats, archive_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    archive_bytes = archive_path.stat().st_size
    if prune_source:
        shutil.rmtree(source_path)
        action = "compressed-and-pruned"
        message = (
            f"archived {source_stats.file_count} files "
            f"({format_mib(source_stats.total_bytes)} -> {format_mib(archive_bytes)})"
        )
    else:
        action = "compressed"
        message = (
            f"archived {source_stats.file_count} files "
            f"({format_mib(source_stats.total_bytes)} -> {format_mib(archive_bytes)}); "
            "source retained"
        )

    return ActionResult(
        target,
        action,
        message,
        archive_path,
        source_bytes=source_stats.total_bytes,
        archive_bytes=archive_bytes,
    )


def restore_target(
    root: Path,
    target: str,
    archive_dir: Path,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> ActionResult:
    target = validate_target_name(target)
    archive_path = archive_path_for(archive_dir, target)
    source_path = root / target

    if not archive_path.exists():
        return ActionResult(target, "skip", "archive missing", archive_path)
    if source_path.exists() and not overwrite:
        return ActionResult(target, "skip", "source already exists; use --overwrite", archive_path)

    manifest = load_manifest(archive_dir)
    manifest_entry = manifest.get("archives", {}).get(target, {})
    expected_file_count = manifest_entry.get("source_file_count")

    if dry_run:
        return ActionResult(target, "would-restore", "would extract archive", archive_path)

    if source_path.exists():
        if source_path.is_dir():
            shutil.rmtree(source_path)
        else:
            source_path.unlink()

    root_resolved = root.resolve()
    with tarfile.open(archive_path, "r:*") as archive:
        members = archive.getmembers()
        for member in members:
            validate_archive_member(member.name, target)
            destination = (root / member.name).resolve()
            if not destination.is_relative_to(root_resolved):
                raise ArchiveError(f"unsafe extraction destination: {destination}")
        archive.extractall(root, members=members)

    restored_stats = collect_tree_stats(source_path)
    if expected_file_count is not None and restored_stats.file_count != expected_file_count:
        raise ArchiveError(
            f"restored {restored_stats.file_count} files; expected {expected_file_count}"
        )

    return ActionResult(
        target,
        "restored",
        f"restored {restored_stats.file_count} files ({format_mib(restored_stats.total_bytes)})",
        archive_path,
        source_bytes=restored_stats.total_bytes,
        archive_bytes=archive_path.stat().st_size,
    )


def status_target(root: Path, target: str, archive_dir: Path) -> ActionResult:
    target = validate_target_name(target)
    source_stats = collect_tree_stats(root / target)
    archive_path = archive_path_for(archive_dir, target)
    archive_exists = archive_path.exists()
    source_status = (
        f"source {format_mib(source_stats.total_bytes)} in {source_stats.file_count} files"
        if source_stats.exists
        else "source missing"
    )
    archive_status = (
        f"archive {format_mib(archive_path.stat().st_size)}"
        if archive_exists
        else "archive missing"
    )
    return ActionResult(
        target,
        "status",
        f"{source_status}; {archive_status}",
        archive_path if archive_exists else None,
        source_bytes=source_stats.total_bytes,
        archive_bytes=archive_path.stat().st_size if archive_exists else 0,
    )


def print_result(result: ActionResult, root: Path) -> None:
    archive = ""
    if result.archive_path:
        try:
            archive = f" ({result.archive_path.relative_to(root)})"
        except ValueError:
            archive = f" ({result.archive_path})"
    print(f"[{result.action}] {result.target}: {result.message}{archive}")


def add_target_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--targets",
        nargs="+",
        default=list(DEFAULT_TARGETS),
        choices=DEFAULT_TARGETS,
        help="Generated directories to operate on.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compress or restore ignored Zillow generated outputs."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root. Defaults to the parent of this script.",
    )
    parser.add_argument(
        "--archive-dir",
        default=DEFAULT_ARCHIVE_DIR,
        help="Archive directory, relative to --root unless absolute.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Show source and archive state.")
    add_target_argument(status_parser)

    compress_parser = subparsers.add_parser("compress", help="Archive generated outputs.")
    add_target_argument(compress_parser)
    compress_parser.add_argument("--force", action="store_true", help="Replace existing archives.")
    compress_parser.add_argument("--dry-run", action="store_true", help="Show planned work only.")
    compress_parser.add_argument(
        "--min-size-mib",
        type=float,
        default=0.0,
        help="Only compress a target at or above this size.",
    )
    compress_parser.add_argument(
        "--prune-source",
        action="store_true",
        help="Delete the uncompressed directory after archive verification.",
    )

    auto_parser = subparsers.add_parser(
        "auto",
        help="Compress large generated outputs and prune sources after verification.",
    )
    add_target_argument(auto_parser)
    auto_parser.add_argument("--force", action="store_true", help="Replace existing archives.")
    auto_parser.add_argument("--dry-run", action="store_true", help="Show planned work only.")
    auto_parser.add_argument(
        "--min-size-mib",
        type=float,
        default=250.0,
        help="Only compress a target at or above this size.",
    )
    auto_parser.add_argument(
        "--keep-source",
        action="store_true",
        help="Keep uncompressed directories instead of pruning them.",
    )

    restore_parser = subparsers.add_parser("restore", help="Restore generated outputs.")
    add_target_argument(restore_parser)
    restore_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing generated directory while restoring.",
    )
    restore_parser.add_argument("--dry-run", action="store_true", help="Show planned work only.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    archive_dir = resolve_archive_dir(root, args.archive_dir)

    try:
        if args.command == "status":
            results = [status_target(root, target, archive_dir) for target in args.targets]
        elif args.command == "compress":
            min_size_bytes = int(args.min_size_mib * MIB)
            results = [
                compress_target(
                    root,
                    target,
                    archive_dir,
                    min_size_bytes=min_size_bytes,
                    prune_source=args.prune_source,
                    force=args.force,
                    dry_run=args.dry_run,
                )
                for target in args.targets
            ]
        elif args.command == "auto":
            min_size_bytes = int(args.min_size_mib * MIB)
            results = [
                compress_target(
                    root,
                    target,
                    archive_dir,
                    min_size_bytes=min_size_bytes,
                    prune_source=not args.keep_source,
                    force=args.force,
                    dry_run=args.dry_run,
                )
                for target in args.targets
            ]
        elif args.command == "restore":
            results = [
                restore_target(
                    root,
                    target,
                    archive_dir,
                    overwrite=args.overwrite,
                    dry_run=args.dry_run,
                )
                for target in args.targets
            ]
        else:
            raise ArchiveError(f"unsupported command: {args.command}")
    except ArchiveError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for result in results:
        print_result(result, root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
