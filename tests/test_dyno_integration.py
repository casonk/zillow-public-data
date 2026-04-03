"""Dyno-lab integration tests for zillow-public-data/refresh.py.

Tests cover: is_non_empty_csv (TempWorkdir), DATE_RE pattern matching,
iter_candidate_paths geography expansion and deduplication, DownloadStats
defaults, and download_all with a mocked HTTP session.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

from dyno_lab.fs import TempWorkdir
from dyno_lab.http import SequenceSession, StaticSession

from refresh import (
    DATE_RE,
    GEOGRAPHIES,
    DownloadStats,
    is_non_empty_csv,
    iter_candidate_paths,
    download_all,
)

# ── is_non_empty_csv with TempWorkdir ─────────────────────────────────────


def test_is_non_empty_csv_valid():
    with TempWorkdir() as wd:
        p = wd.write("valid.csv", "col1,col2\n1,2\n3,4\n")
        assert is_non_empty_csv(p) is True


def test_is_non_empty_csv_empty_file():
    with TempWorkdir() as wd:
        p = wd.write("empty.csv", "")
        assert is_non_empty_csv(p) is False


def test_is_non_empty_csv_header_only():
    with TempWorkdir() as wd:
        p = wd.write("header_only.csv", "col1,col2\n")
        # pandas read_csv with nrows=1 returns empty df for header-only
        assert is_non_empty_csv(p) is False


def test_is_non_empty_csv_missing_file():
    with TempWorkdir() as wd:
        missing = wd.path / "does_not_exist.csv"
        # pandas raises FileNotFoundError which propagates (not EmptyDataError)
        with pytest.raises(Exception):
            is_non_empty_csv(missing)


# ── DATE_RE pattern matching ───────────────────────────────────────────────


@pytest.mark.parametrize("date", ["2024-01-01", "2025-12-31", "2000-06-15"])
def test_date_re_valid(date):
    assert DATE_RE.match(date) is not None


@pytest.mark.parametrize(
    "bad", ["2024/01/01", "01-01-2024", "2024-1-1", "not-a-date", ""]
)
def test_date_re_invalid(bad):
    assert DATE_RE.match(bad) is None


# ── iter_candidate_paths ──────────────────────────────────────────────────


def test_iter_candidate_paths_all_six_geographies():
    doc_urls = {"zhvi": "zhvi/Metro_zhvi_uc_sfr_month.csv"}
    candidates = list(iter_candidate_paths(doc_urls))
    assert len(candidates) == len(GEOGRAPHIES)
    for geo in GEOGRAPHIES:
        assert any(geo in c for c in candidates)


def test_iter_candidate_paths_non_metro_passthrough():
    doc_urls = {"city": "zhvi/City_zhvi_uc_sfr_month.csv"}
    candidates = list(iter_candidate_paths(doc_urls))
    assert candidates == ["zhvi/City_zhvi_uc_sfr_month.csv"]


def test_iter_candidate_paths_deduplication():
    doc_urls = {
        "a": "zhvi/Metro_zhvi_uc_sfr_month.csv",
        "b": "zhvi/Metro_zhvi_uc_sfr_month.csv",  # duplicate Metro path
    }
    candidates = list(iter_candidate_paths(doc_urls))
    assert len(candidates) == len(set(candidates)), "duplicates should be removed"
    assert len(candidates) == len(GEOGRAPHIES)


def test_iter_candidate_paths_mixed_metro_and_plain():
    doc_urls = {
        "metro": "zhvi/Metro_zhvi_uc_sfr_month.csv",
        "city": "zhvi/City_zhvi_uc_sfr_month.csv",
    }
    candidates = list(iter_candidate_paths(doc_urls))
    # Metro expands to 6, City is passthrough but also produced via Metro expansion
    assert len(candidates) == len(set(candidates))
    assert "zhvi/City_zhvi_uc_sfr_month.csv" in candidates


# ── DownloadStats fields and defaults ─────────────────────────────────────


def test_download_stats_defaults():
    stats = DownloadStats()
    assert stats.downloaded == 0
    assert stats.skipped == 0
    assert stats.missing == 0
    assert stats.empty == 0
    assert stats.failed == 0


def test_download_stats_mutation():
    stats = DownloadStats()
    stats.downloaded += 3
    stats.skipped += 1
    assert stats.downloaded == 3
    assert stats.skipped == 1


# ── download_all with mocked HTTP ─────────────────────────────────────────


class _ByteSession:
    """Thin session mock that returns bytes-capable responses for download_all."""

    def __init__(self, csv_bytes: bytes, status_code: int = 200) -> None:
        self.csv_bytes = csv_bytes
        self.status_code = status_code
        self.call_count = 0

    def get(self, url: str, **kwargs):  # noqa: ANN001
        self.call_count += 1

        class _R:
            pass

        r = _R()
        r.status_code = self.status_code
        r.content = self.csv_bytes
        return r


def test_download_all_increments_downloaded_on_200():
    csv_content = b"col1,col2\n1,2\n"
    session = _ByteSession(csv_content, status_code=200)
    doc_urls = {"zhvi": "Metro_zhvi_uc_sfr_month.csv"}

    with TempWorkdir() as wd:
        with patch("refresh.DATA_DIR", wd.path):
            stats = download_all(doc_urls, session, resume=False)

    assert stats.downloaded == len(GEOGRAPHIES)
    assert stats.failed == 0


def test_download_all_skips_existing_non_empty_csv():
    csv_content = b"col1,col2\n1,2\n"
    doc_urls = {"city": "City_zhvi_uc_sfr_month.csv"}

    with TempWorkdir() as wd:
        existing = wd.path / "City_zhvi_uc_sfr_month.csv"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_bytes(csv_content)

        session = _ByteSession(csv_content, status_code=200)
        with patch("refresh.DATA_DIR", wd.path):
            stats = download_all(doc_urls, session, resume=True)

    assert stats.skipped == 1
    assert stats.downloaded == 0


def test_download_all_404_increments_missing():
    session = _ByteSession(b"", status_code=404)
    doc_urls = {"city": "City_data.csv"}

    with TempWorkdir() as wd:
        with patch("refresh.DATA_DIR", wd.path):
            stats = download_all(doc_urls, session, resume=False)

    assert stats.missing == 1
    assert stats.downloaded == 0
