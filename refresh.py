import argparse
import os
import pickle
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
VIZ_DIR = ROOT / "viz"
DOC_URLS_PATH = ROOT / "doc_urls.pickle"
PUBLIC_BASES = (
    "https://files.zillowstatic.com/research/public_csvs/",
    "https://files.zillowstatic.com/research/public_v2/",
)
GEOGRAPHIES = ("Metro", "State", "County", "City", "Zip", "Neighborhood")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class DownloadStats:
    downloaded: int = 0
    skipped: int = 0
    missing: int = 0
    empty: int = 0
    failed: int = 0


def load_doc_urls() -> dict[str, str]:
    with DOC_URLS_PATH.open("rb") as handle:
        return pickle.load(handle)


def iter_candidate_paths(doc_urls: dict[str, str]) -> Iterable[str]:
    seen: set[str] = set()
    for path in doc_urls.values():
        if "Metro" in path:
            for geography in GEOGRAPHIES:
                candidate = path.replace("Metro", geography)
                if candidate not in seen:
                    seen.add(candidate)
                    yield candidate
        elif path not in seen:
            seen.add(path)
            yield path


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    VIZ_DIR.mkdir(exist_ok=True)


def is_non_empty_csv(path: Path) -> bool:
    try:
        df = pd.read_csv(path, nrows=1)
    except pd.errors.EmptyDataError:
        return False
    return not df.empty


def download_all(
    doc_urls: dict[str, str], session: requests.Session, resume: bool = False
) -> DownloadStats:
    stats = DownloadStats()
    timestamp = int(pd.Timestamp.now("UTC").timestamp())
    candidates = list(iter_candidate_paths(doc_urls))
    total = len(candidates)

    for index, path in enumerate(candidates, start=1):
        target = DATA_DIR / path
        target.parent.mkdir(parents=True, exist_ok=True)

        if resume and target.exists() and is_non_empty_csv(target):
            stats.skipped += 1
            continue

        downloaded = False
        for base in PUBLIC_BASES:
            url = f"{base}{path}?t={timestamp}"
            try:
                response = session.get(url, timeout=120)
            except requests.RequestException as exc:
                print(f"[download] request failed for {path} via {base}: {exc}")
                continue

            if response.status_code != 200:
                continue

            target.write_bytes(response.content)
            if not is_non_empty_csv(target):
                target.unlink(missing_ok=True)
                stats.empty += 1
                print(f"[download] empty csv removed: {path}")
            else:
                stats.downloaded += 1
                print(f"[download] {index}/{total} saved {path}")
            downloaded = True
            break

        if downloaded:
            continue

        stats.missing += 1
        print(f"[download] {index}/{total} unavailable: {path}")

    return stats


def date_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in df.columns if DATE_RE.match(str(column))]


def prepare_plot_environment() -> None:
    mpl_config_dir = Path(os.environ.get("MPLCONFIGDIR", "/tmp/mplconfig-zillow"))
    mpl_config_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(mpl_config_dir)

    import matplotlib

    matplotlib.use("Agg")


def make_selections() -> dict[str, tuple[list[object], str | None]]:
    return {
        "Metro": (["Ann Arbor, MI", "Detroit, MI"], "MI"),
        "Zip": (
            [
                48374,
                48375,
                48167,
                48335,
                48336,
                48152,
                48240,
                48168,
                48154,
                48239,
                48170,
                48150,
            ],
            "MI",
        ),
        "City": (
            [
                "Plymouth",
                "Farmington",
                "Farmington Hills",
                "Novi",
                "Livonia",
                "Northville",
                "Redford",
                "Franklin",
                "Wixom",
                "Commerce",
            ],
            "MI",
        ),
        "County": (
            [
                "Oakland County",
                "Wayne County",
                "Livingston County",
                "Washtenaw County",
                "Genesee County",
            ],
            "MI",
        ),
        "State": (
            ["Michigan", "Oregon", "Washington", "California", "Colorado", "Utah"],
            None,
        ),
        "Neighborhood": (
            [
                "SMB Estates",
                "Clements Circle",
                "Coventry Gardens",
                "Woodbury Park",
                "Willow Woods",
            ],
            "MI",
        ),
    }


def plot_all(doc_urls: dict[str, str]) -> int:
    prepare_plot_environment()
    import matplotlib.pyplot as plt

    selections = make_selections()
    plots_written = 0
    seen_paths: set[str] = set()

    for description, original_path in doc_urls.items():
        for geography, (regions, state_name) in selections.items():
            path = (
                original_path.replace("Metro", geography)
                if "Metro" in original_path
                else original_path
            )
            if path in seen_paths:
                continue
            if not Path(path).name.startswith(f"{geography}_"):
                continue
            seen_paths.add(path)

            csv_path = DATA_DIR / path
            if not csv_path.exists():
                continue

            try:
                df = pd.read_csv(csv_path, low_memory=False)
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, encoding="latin-1", low_memory=False)
            except Exception as exc:
                print(f"[viz] failed to read {path}: {exc}")
                continue

            if state_name and "StateName" in df.columns:
                df = df[df["StateName"] == state_name]
            if "RegionName" not in df.columns:
                continue

            selected = df[df["RegionName"].isin(regions)].set_index("RegionName")
            if selected.empty:
                continue

            plot_dates = date_columns(selected)
            if not plot_dates:
                continue

            plot_df = selected[plot_dates].T.apply(pd.to_numeric, errors="coerce")
            plot_df = plot_df.dropna(axis=0, how="all").dropna(axis=1, how="all")
            if plot_df.empty:
                continue

            try:
                ax = plot_df.plot(
                    figsize=(20, 10),
                    xlabel="Date",
                    ylabel=description,
                    title=f"{description} in {regions}",
                )
                figure = ax.get_figure()
                output_path = VIZ_DIR / f"{Path(path).name}.png"
                figure.savefig(output_path)
                plt.close(figure)
                plots_written += 1
                print(f"[viz] wrote {output_path.relative_to(ROOT)}")
            except Exception as exc:
                print(f"[viz] failed to plot {path}: {exc}")
                continue

    return plots_written


def latest_date_for(path: str) -> str | None:
    csv_path = DATA_DIR / path
    if not csv_path.exists():
        return None
    try:
        df = pd.read_csv(csv_path, nrows=1)
    except Exception:
        return None
    dates = date_columns(df)
    return dates[-1] if dates else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh Zillow public data and plots.")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Use existing ./data instead of redownloading.",
    )
    parser.add_argument("--skip-viz", action="store_true", help="Skip plot generation.")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip valid CSVs that already exist in ./data.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    doc_urls = load_doc_urls()

    session = requests.Session()
    session.headers.update({"User-Agent": "zillow-public-data-refresh/1.0"})

    if not args.skip_download:
        stats = download_all(doc_urls, session, resume=args.resume)
        print(
            "[summary] downloads="
            f"{stats.downloaded} skipped={stats.skipped} missing={stats.missing} empty={stats.empty} failed={stats.failed}"
        )

    if not args.skip_viz:
        plots_written = plot_all(doc_urls)
        print(f"[summary] plots={plots_written}")

    sample_paths = [
        "zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
        "median_sale_price/Metro_median_sale_price_uc_sfrcondo_sm_month.csv",
        "invt_fs/City_invt_fs_uc_sfr_month.csv",
    ]
    for sample_path in sample_paths:
        latest = latest_date_for(sample_path)
        if latest:
            print(f"[latest] {sample_path} -> {latest}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
