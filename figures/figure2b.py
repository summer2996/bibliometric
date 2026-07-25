from collections import Counter, defaultdict
from pathlib import Path
import re
import sys
import unicodedata

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import CSV_DIR, END_YEAR, START_YEAR, apply_plot_style, load_analysis_data, save_figure


def _split_names(value):
    """Split an author field without removing duplicates, preserving AU/AU_IN positions."""
    if pd.isna(value):
        return []
    return [re.sub(r"\s+", " ", item).strip(" ,.;") for item in str(value).split(";") if item.strip(" ,.;")]


def _name_signature(full_name):
    """Create a conservative identity key and merge only obvious spelling variants."""
    text = re.sub(r"\\[A-Za-z]+\{([^{}]+)\}", r"\1", str(full_name))
    text = re.sub(r"\\[`'^\"~=]\{?([A-Za-z])\}?", r"\1", text)
    text = re.sub(r"\\[RVrv](?=[A-Za-z])", "", text)
    text = text.replace("{", "").replace("}", "")
    text = unicodedata.normalize("NFKD", text.upper()).encode("ascii", "ignore").decode()
    tokens = re.findall(r"[A-Z]+", text)
    if len(tokens) < 2:
        return ""

    # Bibliometrix AU stores names as SURNAME GIVEN-NAME(S).  Full middle names and
    # their initials are treated alike: BARBARA JANE and BARBARA J -> BARBARA|J.
    surname, given = tokens[0], tokens[1:]
    return "|".join([surname, given[0], "".join(token[0] for token in given[1:])])


def _save_ambiguity_audit(excluded):
    csv_path = CSV_DIR / "figure2b_excluded_ambiguous_authors.csv"
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    excluded.to_csv(csv_path, index=False)


def prepare_data():
    data = load_analysis_data()
    author_counts = Counter()
    yearly_counts = Counter()
    signatures = defaultdict(Counter)
    full_names = defaultdict(Counter)

    for row in data[["AU_IN", "AU", "PY"]].itertuples(index=False):
        initials = _split_names(row.AU_IN)
        complete_names = _split_names(row.AU)
        year = int(row.PY)

        # Count an author at most once per article.
        for author in dict.fromkeys(initials):
            author_counts[author] += 1
            yearly_counts[(author, year)] += 1

        if len(initials) == len(complete_names):
            for author, complete_name in zip(initials, complete_names):
                signature = _name_signature(complete_name)
                if signature:
                    signatures[author][signature] += 1
                    full_names[author][complete_name] += 1

    excluded_rows = []
    excluded_authors = set()

    for author, records in author_counts.items():
        identity_count = len(signatures[author])
        names = "; ".join(
            f"{name} ({count})" for name, count in full_names[author].most_common()
        ) or "无可靠完整姓名"

        if author.upper() == "NA NA":
            excluded_authors.add(author)
            excluded_rows.append(
                {
                    "author": author,
                    "records": records,
                    "matched_full_names": names,
                    "reason": "缺少可靠的完整姓名映射",
                }
            )
        elif identity_count == 0:
            continue
        elif identity_count > 1:
            excluded_authors.add(author)
            excluded_rows.append(
                {
                    "author": author,
                    "records": records,
                    "matched_full_names": names,
                    "reason": f"对应 {identity_count} 个不兼容的完整姓名",
                }
            )

    excluded = pd.DataFrame(
        excluded_rows,
        columns=["author", "records", "matched_full_names", "reason"],
    ).sort_values(
        ["records", "author"], ascending=[False, True]
    )
    _save_ambiguity_audit(excluded)

    rows = [
        (author, year, records)
        for (author, year), records in yearly_counts.items()
        if author not in excluded_authors
    ]
    long = pd.DataFrame(rows, columns=["author", "year", "records"])
    totals = long.groupby("author")["records"].sum().sort_values(ascending=False)
    top = totals.head(10).index
    result = long[long["author"].isin(top)].copy()
    result["total"] = result.groupby("author")["records"].transform("sum")
    return result.sort_values(["total", "author", "year"], ascending=[False, True, True])


def create_figure(data):
    apply_plot_style()
    pivot = data.pivot(index="author", columns="year", values="records").fillna(0)
    totals = pivot.sum(axis=1).sort_values(ascending=True)
    pivot = pivot.loc[totals.index].reindex(columns=range(START_YEAR, END_YEAR + 1), fill_value=0)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    colors = plt.cm.viridis([i / max(1, len(pivot.columns) - 1) for i in range(len(pivot.columns))])
    pivot.plot.barh(stacked=True, ax=ax, color=colors, width=0.78)
    for y, total in enumerate(totals):
        ax.text(total + max(totals) * 0.01, y, str(int(total)), va="center", fontsize=8)
    ax.set(title="Top 10 active authors: annual productivity", xlabel="Records", ylabel="")
    ax.legend(title="Year", ncol=4, fontsize=7, title_fontsize=8, loc="lower right")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    plotting_data = prepare_data()
    figure = create_figure(plotting_data)
    save_figure(figure, plotting_data, "figure2b")
    plt.close(figure)
