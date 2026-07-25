from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import (
    apply_plot_style,
    load_database_data,
    load_master_data,
    normalize_doi,
    normalize_title,
    save_figure,
)


SOURCE_FILES = {
    "IEEE": "IEEE.RData",
    "ACM": "acm.RData",
    "Scopus": "scopus.RData",
    "WoS": "wos.RData",
}

COMBINATIONS = [
    (("ACM",), "ACM only"),
    (("Scopus",), "Scopus only"),
    (("WoS",), "WoS only"),
    (("ACM", "WoS"), "ACM+WoS"),
    (("IEEE",), "IEEE only"),
    (("Scopus", "WoS"), "Scopus+WoS"),
    (("ACM", "Scopus", "WoS"), "ACM+Scopus+WoS"),
    (("ACM", "Scopus"), "ACM+Scopus"),
    (("IEEE", "Scopus"), "IEEE+Scopus"),
    (("IEEE", "Scopus", "WoS"), "IEEE+Scopus+WoS"),
    (("IEEE", "WoS"), "IEEE+WoS"),
    (("IEEE", "ACM"), "IEEE+ACM"),
    (("IEEE", "ACM", "Scopus", "WoS"), "All four"),
    (("IEEE", "ACM", "WoS"), "IEEE+ACM+WoS"),
]


def _index_map(values):
    result = {}
    for index, value in values.items():
        if value:
            result.setdefault(value, []).append(index)
    return result


def prepare_data():
    master = load_master_data().reset_index(drop=True)
    master_doi = master["DI_norm" if "DI_norm" in master else "DI"].map(normalize_doi)
    master_title = master["TI_norm" if "TI_norm" in master else "TI"].map(normalize_title)
    doi_map = _index_map(master_doi)
    title_map = _index_map(master_title)
    memberships = [set() for _ in range(len(master))]
    source_sizes = {}

    for source, filename in SOURCE_FILES.items():
        records = load_database_data(filename)
        source_sizes[source] = len(records)
        for _, row in records.iterrows():
            doi = normalize_doi(row.get("DI"))
            title = normalize_title(row.get("TI"))
            candidates = doi_map.get(doi, []) if doi else []
            if not candidates and title:
                candidates = title_map.get(title, [])
            if not candidates:
                continue
            if len(candidates) > 1:
                same_source = [
                    index
                    for index in candidates
                    if str(master.loc[index, "DB_SOURCE"]).lower() == source.lower()
                ]
                selected = same_source[0] if len(same_source) == 1 else candidates[0]
            else:
                selected = candidates[0]
            memberships[selected].add(source)

    for index, membership in enumerate(memberships):
        if not membership:
            membership.add(str(master.loc[index, "DB_SOURCE"]))

    membership_keys = [
        tuple(source for source in SOURCE_FILES if source in membership)
        for membership in memberships
    ]
    counts = pd.Series(membership_keys).value_counts()
    observed_sizes = {
        source: sum(count for combination, count in counts.items() if source in combination)
        for source in SOURCE_FILES
    }
    if observed_sizes != source_sizes:
        raise RuntimeError(
            f"Database-overlap marginals do not match source files: "
            f"expected={source_sizes}, observed={observed_sizes}"
        )
    rows = [
        {
            "database_combination": label,
            "records": int(counts.get(combination, 0)),
            "number_of_databases": len(combination),
        }
        for combination, label in COMBINATIONS
    ]
    return (
        pd.DataFrame(rows)
        .sort_values(
            ["number_of_databases", "records"],
            ascending=[True, False],
        )
        .reset_index(drop=True)
    )


def create_figure(data):
    apply_plot_style()
    shown = data.iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    bars = ax.barh(
        shown["database_combination"],
        shown["records"],
        color="#377EAD",
    )
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set(
        title="Database overlap after deduplication",
        xlabel="Unique records",
        ylabel="",
    )
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    plotting_data = prepare_data()
    figure = create_figure(plotting_data)
    save_figure(figure, plotting_data, "figure1b")
    plt.close(figure)
