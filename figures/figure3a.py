from pathlib import Path
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import apply_plot_style, load_analysis_data, normalize_source, save_figure, shorten


def prepare_data():
    data = load_analysis_data()
    sources = data["SO"].map(normalize_source).dropna()
    return sources.value_counts().head(10).rename_axis("source").reset_index(name="records")


def create_figure(data):
    apply_plot_style()
    shown = data.iloc[::-1].copy()
    shown["label"] = shown["source"].map(lambda x: shorten(x.title(), 45))
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    positions = range(len(shown))
    bars = ax.barh(positions, shown["records"], color="#4C78A8")
    ax.set_yticks(list(positions), shown["label"])
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set(title="Top publication sources", xlabel="Records", ylabel="")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    plotting_data = prepare_data()
    figure = create_figure(plotting_data)
    save_figure(figure, plotting_data, "figure3a")
    plt.close(figure)
