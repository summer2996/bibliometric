from pathlib import Path
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import apply_plot_style, extract_country, load_analysis_data, save_figure


def prepare_data():
    data = load_analysis_data()
    countries = data.apply(extract_country, axis=1).dropna()
    return countries.value_counts().head(10).rename_axis("country").reset_index(name="records")


def create_figure(data):
    apply_plot_style()
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    bars = ax.bar(data["country"], data["records"], color="#3C8DBC")
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set(title="Top 10 corresponding-author countries", xlabel="", ylabel="Records")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    plotting_data = prepare_data()
    figure = create_figure(plotting_data)
    save_figure(figure, plotting_data, "figure3b")
    plt.close(figure)
