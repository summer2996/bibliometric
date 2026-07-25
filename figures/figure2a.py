from pathlib import Path
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import END_YEAR, START_YEAR, apply_plot_style, load_analysis_data, save_figure


def prepare_data():
    data = load_analysis_data()
    years = range(START_YEAR, END_YEAR + 1)
    counts = data["PY"].value_counts().reindex(years, fill_value=0)
    return counts.rename_axis("year").reset_index(name="records")


def create_figure(data):
    apply_plot_style()
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.plot(data["year"], data["records"], color="#337DB4", marker="o", linewidth=2)
    ax.fill_between(data["year"], data["records"], color="#9ECAE1", alpha=0.55)
    for row in data.itertuples():
        ax.annotate(str(row.records), (row.year, row.records), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8)
    ax.set(title="Annual publication records", xlabel="Year", ylabel="Records", xticks=data["year"])
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    plotting_data = prepare_data()
    figure = create_figure(plotting_data)
    save_figure(figure, plotting_data, "figure2a")
    plt.close(figure)
