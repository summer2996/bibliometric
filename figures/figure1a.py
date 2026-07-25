from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import apply_plot_style, load_database_data, save_figure


DATABASES = [
    ("IEEE Xplore", "IEEE.RData", "#4C78A8"),
    ("ACM DL", "acm.RData", "#F2A900"),
    ("Scopus", "scopus.RData", "#59A14F"),
    ("Web of Science", "wos.RData", "#9D9D9D"),
]


def prepare_data():
    rows = []
    for database, filename, color in DATABASES:
        rows.append(
            {
                "database": database,
                "records": len(load_database_data(filename)),
                "color": color,
            }
        )
    return pd.DataFrame(rows)


def create_figure(data):
    apply_plot_style()
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    bars = ax.bar(data["database"], data["records"], color=data["color"])
    ax.bar_label(bars, padding=3)
    ax.set(
        title="Initial records retrieved by database",
        xlabel="Database",
        ylabel="Raw records",
    )
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    plotting_data = prepare_data()
    figure = create_figure(plotting_data)
    save_figure(figure, plotting_data.drop(columns="color"), "figure1a")
    plt.close(figure)
