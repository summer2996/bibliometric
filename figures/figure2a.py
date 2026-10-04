from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import END_YEAR, START_YEAR, apply_plot_style, load_analysis_data, save_figure


def prepare_data():
    data = load_analysis_data()
    years = range(START_YEAR, END_YEAR + 1)
    counts = data["PY"].value_counts().reindex(years, fill_value=0)
    annual = counts.rename_axis("year").reset_index(name="records")

    if int(annual.loc[annual["year"].eq(2025), "records"].iloc[0]) != 762:
        raise ValueError("Expected 2025 to contain 762 records.")
    annual["partial_year"] = annual["year"].eq(2026)
    annual["label"] = annual["records"].astype(int).astype(str)
    annual.loc[annual["partial_year"], "label"] += "*"
    return annual


def _add_stage_band(ax, start, end, y, height, color, label):
    patch = FancyBboxPatch(
        (start - 0.45, y),
        end - start + 0.90,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.18",
        linewidth=0,
        facecolor=color,
        alpha=0.80,
        clip_on=False,
        zorder=0,
    )
    ax.add_patch(patch)
    ax.text(
        (start + end) / 2,
        y + height / 2,
        label,
        ha="center",
        va="center",
        fontsize=6.2,
        color="#202020",
        linespacing=0.95,
        clip_on=False,
    )


def create_figure(data):
    apply_plot_style()
    fig, ax = plt.subplots(figsize=(7.15, 4.05))

    ax.plot(
        data["year"],
        data["records"],
        color="#2D7DBB",
        marker="o",
        markersize=4.2,
        markerfacecolor="#2D7DBB",
        markeredgecolor="white",
        markeredgewidth=0.65,
        linewidth=1.7,
        zorder=3,
    )
    ax.fill_between(data["year"], data["records"], color="#B9D9EB", alpha=0.78, zorder=1)

    for row in data.itertuples():
        offset = 7 if not row.partial_year else 8
        ax.annotate(
            row.label,
            (row.year, row.records),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            fontsize=6.9,
            color="#202020",
            zorder=4,
        )

    stage_totals = {
        "2016-2018": int(data[data["year"].between(2016, 2018)]["records"].sum()),
        "2019-2022": int(data[data["year"].between(2019, 2022)]["records"].sum()),
        "2023-May 2026": int(data[data["year"].between(2023, 2026)]["records"].sum()),
    }
    band_y = -90
    band_height = 47
    _add_stage_band(ax, 2016, 2018, band_y, band_height, "#FFF56E", f"2016-2018\n{stage_totals['2016-2018']} records")
    _add_stage_band(ax, 2019, 2022, band_y, band_height, "#A5F36C", f"2019-2022\n{stage_totals['2019-2022']} records")
    _add_stage_band(ax, 2023, 2026, band_y, band_height, "#2ED3E6", f"2023-May 2026\n{stage_totals['2023-May 2026']} records")

    ax.text(
        2016.0,
        785,
        "2026* = records available\nthrough May 2026",
        ha="left",
        va="center",
        fontsize=6.5,
        color="#333333",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#BFBFBF", "linewidth": 0.45, "alpha": 0.92},
    )

    ax.set(
        title="Annual Publication Records",
        xlabel="Year",
        ylabel="Records",
        xticks=data["year"],
        xlim=(2015.55, 2026.45),
        ylim=(-110, 830),
    )
    ax.grid(axis="y", alpha=0.26)
    ax.grid(axis="x", alpha=0.16)
    ax.spines["top"].set_color("#BFBFBF")
    ax.spines["right"].set_color("#BFBFBF")
    fig.subplots_adjust(left=0.075, right=0.985, top=0.91, bottom=0.22)
    return fig


if __name__ == "__main__":
    plotting_data = prepare_data()
    figure = create_figure(plotting_data)
    save_figure(figure, plotting_data[["year", "records"]], "figure2a")
    plt.close(figure)
