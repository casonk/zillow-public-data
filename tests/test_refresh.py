import pandas as pd

from refresh import DATE_RE, iter_candidate_paths, load_doc_urls


def test_load_doc_urls_not_empty():
    doc_urls = load_doc_urls()
    assert isinstance(doc_urls, dict)
    assert doc_urls, "doc_urls.pickle should export at least one entry"


def test_iter_candidate_paths_has_all_geographies():
    doc_urls = {"example": "zhvi/Metro_zhvi_uc_sfr_month.csv"}
    candidates = list(iter_candidate_paths(doc_urls))
    assert len(candidates) == len({"Metro", "State", "County", "City", "Zip", "Neighborhood"})
    assert all(
        "Metro" not in candidate or candidate.endswith("_month.csv") for candidate in candidates
    )


def test_date_columns_matches_iso_dates():
    df = pd.DataFrame(
        {
            "RegionName": ["A", "B"],
            "2025-12-31": [1, 2],
            "2026-01-31": [3, 4],
            "NotADate": [0, 0],
        }
    )
    dates = [col for col in df.columns if DATE_RE.match(col)]
    assert "2026-01-31" in dates
    assert "NotADate" not in dates


def test_date_columns_with_non_string():
    df = pd.DataFrame({1: [1], "2026-01-31": [2]})
    dates = [col for col in df.columns if DATE_RE.match(str(col))]
    assert dates == ["2026-01-31"]
