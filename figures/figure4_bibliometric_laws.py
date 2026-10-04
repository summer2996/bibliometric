from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import CSV_DIR, PDF_DIR, PNG_DIR, END_YEAR, apply_plot_style, load_analysis_data, normalize_source, save_figure, split_terms


COLORS = {
    "blue": "#2F6F9F",
    "red": "#C44E52",
    "orange": "#F58518",
    "green": "#54A24B",
    "purple": "#7A5195",
    "gray": "#6B7280",
}


def _set_paper_style():
    apply_plot_style()
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "legend.fontsize": 7,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "lines.linewidth": 1.35,
            "patch.linewidth": 0.4,
        }
    )


def _split_authors(value):
    return [author.upper() for author in split_terms(value) if author.upper() != "NA NA"]


def _citation_bin(value):
    bins = [
        (0, 0, "0"),
        (1, 1, "1"),
        (2, 4, "2-4"),
        (5, 9, "5-9"),
        (10, 24, "10-24"),
        (25, 49, "25-49"),
        (50, 99, "50-99"),
        (100, np.inf, "100+"),
    ]
    for lower, upper, label in bins:
        if lower <= value <= upper:
            return label
    return "100+"


def _bradford_zones(source_counts):
    total_records = int(source_counts["records"].sum())
    target = total_records / 3
    zone = 1
    running = 0
    zones = []
    for records in source_counts["records"]:
        if zone < 3 and running >= target * zone:
            zone += 1
        zones.append(zone)
        running += records
    source_counts = source_counts.copy()
    source_counts["bradford_zone"] = zones
    summary = (
        source_counts.groupby("bradford_zone", as_index=False)
        .agg(sources=("source", "count"), records=("records", "sum"))
        .sort_values("bradford_zone")
    )
    summary["zone_label"] = summary["bradford_zone"].map(lambda value: f"Zone {value}")
    summary["record_share"] = summary["records"] / total_records if total_records else 0
    return source_counts, summary


def prepare_data():
    data = load_analysis_data()

    annual = data["PY"].value_counts().sort_index().rename_axis("year").reset_index(name="records")
    annual["is_partial_year"] = annual["year"].eq(END_YEAR)
    annual["year_label"] = annual["year"].astype(int).astype(str)
    annual.loc[annual["is_partial_year"], "year_label"] += "*"
    complete = annual[~annual["is_partial_year"] & annual["records"].gt(0)]
    years = complete["year"].to_numpy(dtype=float)
    records = complete["records"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(years, np.log(records), 1)
    annual["price_fit"] = np.exp(intercept + slope * annual["year"].to_numpy(dtype=float))
    annual["exponential_growth_rate"] = np.exp(slope) - 1
    annual["fit_note"] = "Exponential fit excludes the incomplete 2026 record."

    source_counts = (
        data["SO"]
        .map(normalize_source)
        .dropna()
        .value_counts()
        .rename_axis("source")
        .reset_index(name="records")
    )
    source_counts["rank"] = range(1, len(source_counts) + 1)
    source_counts["cumulative_records"] = source_counts["records"].cumsum()
    source_counts, bradford_summary = _bradford_zones(source_counts)

    author_counts = {}
    for authors in data["AU_IN"].map(_split_authors):
        for author in set(authors):
            author_counts[author] = author_counts.get(author, 0) + 1
    lotka = (
        pd.Series(author_counts)
        .value_counts()
        .sort_index()
        .rename_axis("publications")
        .reset_index(name="authors")
    )
    lotka["log_publications"] = np.log10(lotka["publications"])
    lotka["log_authors"] = np.log10(lotka["authors"])
    if len(lotka) >= 2:
        lotka_slope, lotka_intercept = np.polyfit(lotka["log_publications"], lotka["log_authors"], 1)
        lotka["fitted_distribution"] = 10 ** (lotka_intercept + lotka_slope * lotka["log_publications"])
        lotka["lotka_exponent"] = -lotka_slope
    else:
        lotka["fitted_distribution"] = lotka["authors"]
        lotka["lotka_exponent"] = np.nan
    single_author_count = float(lotka.loc[lotka["publications"].eq(1), "authors"].iloc[0])
    lotka["theoretical_distribution"] = single_author_count / (lotka["publications"] ** 2)

    citations = pd.to_numeric(data["TC"], errors="coerce").fillna(0).astype(int)
    citation_distribution = (
        citations.map(_citation_bin)
        .value_counts()
        .reindex(["0", "1", "2-4", "5-9", "10-24", "25-49", "50-99", "100+"], fill_value=0)
        .rename_axis("citation_group")
        .reset_index(name="records")
    )
    citation_distribution["share"] = citation_distribution["records"] / len(data)

    return annual, source_counts, bradford_summary, lotka, citation_distribution


def create_figure(annual, bradford_summary, lotka, citation_distribution):
    _set_paper_style()
    fig, axes = plt.subplots(2, 2, figsize=(7.16, 4.45))

    ax = axes[0, 0]
    ax.plot(annual["year_label"], annual["records"], marker="o", markersize=3.6, color=COLORS["blue"], label="Observed")
    ax.plot(annual["year_label"], annual["price_fit"], linestyle="--", color=COLORS["red"], label="Exponential fit")
    growth = annual["exponential_growth_rate"].iloc[0] * 100
    ax.set(title=f"Price trend: exponential growth rate = {growth:.1f}%", xlabel="Year (* incomplete)", ylabel="Records")
    ax.legend(frameon=False, loc="upper left")
    ax.annotate("2026* partial", xy=(len(annual) - 1, annual["records"].iloc[-1]), xytext=(-35, 17), textcoords="offset points", fontsize=6.8, arrowprops={"arrowstyle": "->", "lw": 0.6, "color": COLORS["gray"]})

    ax = axes[0, 1]
    zone_colors = [COLORS["blue"], COLORS["orange"], COLORS["green"]]
    bars = ax.bar(bradford_summary["zone_label"], bradford_summary["records"], color=zone_colors, width=0.62)
    ax.set(title="Bradford zones", xlabel="Equal-output source zones", ylabel="Records")
    ax.bar_label(bars, labels=[f"{row.records}\n{row.sources} sources" for row in bradford_summary.itertuples()], fontsize=7, padding=2)
    ax.set_ylim(0, bradford_summary["records"].max() * 1.22)

    ax = axes[1, 0]
    ax.scatter(lotka["publications"], lotka["authors"], color=COLORS["blue"], s=18, label="Observed", zorder=3)
    ax.plot(lotka["publications"], lotka["fitted_distribution"], color=COLORS["red"], linestyle="--", label=f"Fitted n={lotka['lotka_exponent'].iloc[0]:.2f}")
    ax.plot(lotka["publications"], lotka["theoretical_distribution"], color=COLORS["green"], linestyle=":", label="Theoretical n=2")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set(title="Lotka author productivity", xlabel="Papers per author", ylabel="Authors")
    ax.legend(frameon=False, loc="upper right")

    ax = axes[1, 1]
    bars = ax.bar(citation_distribution["citation_group"], citation_distribution["records"], color=COLORS["purple"], width=0.68)
    ax.set(title="Citation distribution by group", xlabel="Total citations", ylabel="Records")
    ax.bar_label(bars, fontsize=6.5, padding=2)
    ax.tick_params(axis="x", rotation=0)
    ax.set_ylim(0, citation_distribution["records"].max() * 1.18)

    fig.tight_layout(pad=0.55, h_pad=1.0, w_pad=0.9)
    return fig


if __name__ == "__main__":
    annual_data, bradford_data, bradford_zone_data, lotka_data, citation_data = prepare_data()
    figure = create_figure(annual_data, bradford_zone_data, lotka_data, citation_data)
    combined = pd.concat(
        [
            annual_data.assign(panel="price_law"),
            bradford_zone_data.assign(panel="bradford_zones"),
            lotka_data.assign(panel="lotka_law"),
            citation_data.assign(panel="citation_distribution"),
        ],
        ignore_index=True,
        sort=False,
    )
    save_figure(figure, combined, "figure4_bibliometric_laws")
    plt.close(figure)

    for directory in (PNG_DIR, PDF_DIR, CSV_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    annual_data.to_csv(CSV_DIR / "figure4a_price_law.csv", index=False)
    bradford_data.to_csv(CSV_DIR / "figure4b_bradford_law.csv", index=False)
    bradford_zone_data.to_csv(CSV_DIR / "figure4b_bradford_zones.csv", index=False)
    lotka_data.to_csv(CSV_DIR / "figure4c_lotka_law.csv", index=False)
    citation_data.to_csv(CSV_DIR / "figure4d_citation_distribution.csv", index=False)
