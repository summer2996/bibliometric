from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path
import math
import sys
import textwrap

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import CSV_DIR, PDF_DIR, PNG_DIR, apply_plot_style, load_analysis_data, normalize_source, save_figure, split_terms


PALETTE = [
    "#4E79A7",
    "#F28E2B",
    "#59A14F",
    "#E15759",
    "#B07AA1",
    "#76B7B2",
    "#EDC948",
]

REFERENCE_LABELS = {
    "DOI 10.1145/3511861.3511863": "Finnie-Ansley et al. (2022), Robots Are Coming",
    "DOI 10.1145/3501385.3543957": "Sarsa et al. (2022), LLM Exercises",
    "DOI 10.1145/3623762.3633499": "Prather et al. (2023), Robots Are Here",
    "DOI 10.1145/3545945.3569759": "Becker et al. (2023), Programming Is Hard",
    "DOI 10.1145/3587102.3588785": "Leinonen et al. (2023), Code Explanations",
    "DOI 10.1145/3545945.3569770": "Leinonen et al. (2023), Error Messages",
    "DOI 10.1145/3545945.3569823": "Denny et al. (2023), Conversing with Copilot",
    "DOI 10.1145/3576123.3576134": "Finnie-Ansley et al. (2023), Codex in CS2",
    "DOI 10.1145/3544548.3580919": "Kazemitabaar et al. (2023), AI Code Generators",
    "DOI 10.1145/3545945.3569785": "SIGCSE 2023 AI/CS Education",
    "DOI 10.1145/3568813.3600138": "Lau and Guo (2023), Instructor Adaptation",
    "DOI 10.1145/3624720": "Denny et al. (2024), Era of Generative AI",
    "DOI 10.1145/3631802.3631830": "Koli Calling 2023 GenAI Study",
    "DOI 10.1145/3632620.3671116": "Prather et al. (2024), Widening Gap",
    "DOI 10.1145/3613904.3642773": "Kazemitabaar et al. (2024), CodeAid",
    "DOI 10.1145/3231711": "Keuning et al. (2018), Feedback Review",
    "DOI 10.1145/3293881.3295779": "Luxton-Reilly et al. (2018), Intro Programming Review",
}

REFERENCE_SHORT_LABELS = {
    "DOI 10.1145/3511861.3511863": "Finnie-Ansley et al. (2022)",
    "DOI 10.1145/3501385.3543957": "Sarsa et al. (2022)",
    "DOI 10.1145/3623762.3633499": "Prather et al. (2023)",
    "DOI 10.1145/3545945.3569759": "Becker et al. (2023)",
    "DOI 10.1145/3587102.3588785": "Leinonen et al. (2023a)",
    "DOI 10.1145/3545945.3569770": "Leinonen et al. (2023b)",
    "DOI 10.1145/3545945.3569823": "Denny et al. (2023)",
    "DOI 10.1145/3576123.3576134": "Finnie-Ansley et al. (2023)",
    "DOI 10.1145/3544548.3580919": "Kazemitabaar et al. (2023)",
    "DOI 10.1145/3568813.3600138": "Lau & Guo (2023)",
    "DOI 10.1145/3624720": "Denny et al. (2024)",
    "DOI 10.1145/3231711": "Keuning et al. (2018)",
    "DOI 10.1145/3293881.3295779": "Luxton-Reilly et al. (2018)",
}

SOURCE_LABEL_PATTERNS = [
    ("Acm Trans. Comput. Educ.", "ACM TOCE"),
    ("Acm Transactions On Computing Education", "ACM TOCE"),
    ("Acm International Conference Proceeding Series", "ACM ICPS"),
    ("Annual Conference On Innovation And Technology In Computer Science Education", "ITiCSE"),
    ("Proceedings Of The 25Th Koli Calling", "Koli Calling 2025"),
    ("Proceedings - Frontiers In Education Conference", "FIE"),
    ("Ieee Access", "IEEE Access"),
    ("Proceedings Of The 56Th Acm Technical Symposium", "SIGCSE TS 2025"),
    ("Proceedings Of The 57Th Acm Technical Symposium", "SIGCSE TS 2026"),
    ("Proceedings Of The 2026 Chi Conference", "CHI 2026"),
    ("Proceedings Of The 2025 Chi Conference", "CHI 2025"),
    ("Acm Trans. Softw. Eng. Methodol.", "ACM TOSEM"),
    ("Lecture Notes In Computer Science", "LNCS"),
    ("Proc. Acm Hum.-Comput. Interact.", "PACM HCI"),
    ("Acm Comput. Surv.", "ACM Computing Surveys"),
    ("Education And Information Technologies", "Education and IT"),
    ("Proceedings Of The 2025 Working Group Reports", "ITiCSE-WGR 2025"),
    ("Iticse 2018 Companion", "ITiCSE Companion 2018"),
]

KNOWN_SOURCE_LABELS = {label for _, label in SOURCE_LABEL_PATTERNS}


def _clean(value):
    return " ".join(str(value).upper().strip(" ,.;").split())


def _groups(series):
    return [[_clean(term) for term in split_terms(value) if _clean(term)] for value in series]


def _keyword_groups(data):
    groups = []
    for row in data.itertuples(index=False):
        terms = [_clean(term) for term in split_terms(getattr(row, "ID", None)) + split_terms(getattr(row, "DE", None))]
        groups.append(list(dict.fromkeys([term for term in terms if term])))
    return groups


def _cooccurrence_graph(groups, top_n=18, min_occurrences=2):
    frequency = Counter(term for group in groups for term in set(group))
    # Preserve deterministic node order so community detection is reproducible.
    selected = [term for term, count in frequency.most_common(top_n) if count >= min_occurrences]
    selected_set = set(selected)
    graph = nx.Graph()
    graph.add_nodes_from(selected)
    for group in groups:
        terms = sorted(set(group) & selected_set)
        for left, right in combinations(terms, 2):
            graph.add_edge(left, right, weight=graph.get_edge_data(left, right, {}).get("weight", 0) + 1)
    graph.remove_nodes_from(list(nx.isolates(graph)))
    return graph, frequency


def _canonical_source(value):
    source = normalize_source(value)
    if not source:
        return None
    title = source.title()
    for pattern, label in SOURCE_LABEL_PATTERNS:
        if title.startswith(pattern):
            return label
    return title


def _source_coupling_graph(data, top_n=18):
    source_refs = {}
    for row in data.itertuples(index=False):
        source = _canonical_source(getattr(row, "SO", None))
        refs = set(_clean(term) for term in split_terms(getattr(row, "CR", None)) if _clean(term))
        if source and refs:
            source_refs.setdefault(source, set()).update(refs)

    source_frequency = Counter({source: len(refs) for source, refs in source_refs.items()})
    top_sources = [source for source, _ in source_frequency.most_common(top_n)]
    graph = nx.Graph()
    graph.add_nodes_from(top_sources)
    sources = list(top_sources)
    for left, right in combinations(sources, 2):
        weight = len(source_refs[left] & source_refs[right])
        if weight:
            graph.add_edge(left, right, weight=weight)
    graph.remove_nodes_from(list(nx.isolates(graph)))
    return graph, source_frequency


def _display_label(node):
    if node in REFERENCE_LABELS:
        return REFERENCE_LABELS[node]
    if node in KNOWN_SOURCE_LABELS:
        return node
    title = node.title()
    for pattern, label in SOURCE_LABEL_PATTERNS:
        if title.startswith(pattern):
            return label
    return title


def _short_label(node, width=25):
    if node in REFERENCE_SHORT_LABELS:
        return REFERENCE_SHORT_LABELS[node]
    label = _display_label(node)
    if len(label) <= width:
        return label
    return textwrap.shorten(label, width=width, placeholder="...")


def _centrality_table(graph, label, frequency, communities=None):
    if not graph:
        return pd.DataFrame()
    degree = dict(graph.degree(weight="weight"))
    # Edge weights are tie strengths, so shortest-path centralities use inverse weight as distance.
    distance_graph = graph.copy()
    for _, _, values in distance_graph.edges(data=True):
        values["distance"] = 1.0 / max(float(values.get("weight", 1.0)), 1e-12)
    betweenness = nx.betweenness_centrality(distance_graph, weight="distance", normalized=True)
    closeness = nx.closeness_centrality(distance_graph, distance="distance")
    rows = []
    for node in graph.nodes:
        rows.append(
            {
                "network": label,
                "node": node,
                "display_label": _display_label(node),
                "cluster": (communities or {}).get(node, ""),
                "weighted_degree": degree.get(node, 0),
                "betweenness": betweenness.get(node, 0),
                "closeness": closeness.get(node, 0),
                "occurrences": frequency.get(node, 0),
            }
        )
    return pd.DataFrame(rows).sort_values(["weighted_degree", "betweenness", "node"], ascending=[False, False, True])


def _detect_communities(graph):
    if not graph:
        return {}
    # A common resolution is used across all three panels for directly comparable three-community maps.
    communities = nx.community.louvain_communities(graph, weight="weight", seed=42, resolution=1.03)
    communities = sorted(communities, key=lambda values: (-len(values), sorted(values)[0]))
    cluster_map = {}
    for index, community in enumerate(communities, start=1):
        for node in community:
            cluster_map[node] = index
    return cluster_map


def _clustered_layout(graph, cluster_map):
    clusters = sorted(set(cluster_map.values()))
    if not clusters:
        return nx.spring_layout(graph, weight="weight", seed=42, k=1.2, iterations=300)

    centers = {}
    radius = 2.55
    for index, cluster in enumerate(clusters):
        angle = 2 * math.pi * index / max(len(clusters), 1)
        centers[cluster] = (radius * math.cos(angle), radius * math.sin(angle))

    positions = {}
    for cluster in clusters:
        nodes = [node for node, value in cluster_map.items() if value == cluster]
        subgraph = graph.subgraph(nodes)
        if len(nodes) == 1:
            local = {nodes[0]: (0.0, 0.0)}
        else:
            local = nx.spring_layout(subgraph, weight="weight", seed=42 + cluster, k=0.95, iterations=300)
        scale = 0.72 + 0.07 * math.sqrt(len(nodes))
        center_x, center_y = centers[cluster]
        for node, (x, y) in local.items():
            positions[node] = (center_x + scale * x, center_y + scale * y)

    positions = nx.spring_layout(graph, pos=positions, fixed=None, weight="weight", seed=42, k=1.7, iterations=90)
    return positions


def _scale(values, minimum, maximum):
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [(minimum + maximum) / 2 for _ in values]
    return [minimum + (value - low) / (high - low) * (maximum - minimum) for value in values]


def _draw_network_map(
    ax,
    graph,
    cluster_map,
    node_metric,
    title,
    label_width=24,
    max_labels=8,
    forced_labels=None,
    label_offsets=None,
    label_alignments=None,
    show_legend=True,
    compact=False,
):
    degree = dict(graph.degree(weight="weight"))
    positions = _clustered_layout(graph, cluster_map)
    weights = [graph[u][v]["weight"] for u, v in graph.edges]
    if compact:
        edge_widths = _scale(weights, 0.18, 1.15)
        edge_alphas = _scale(weights, 0.045, 0.16)
        size_min, size_max = 85, 470
        font_size = 7.0
    else:
        edge_widths = _scale(weights, 0.25, 2.2)
        edge_alphas = _scale(weights, 0.08, 0.28)
        size_min, size_max = 150, 760
        font_size = 7.2

    for (edge, width, alpha) in sorted(
        zip(graph.edges, edge_widths, edge_alphas),
        key=lambda item: graph[item[0][0]][item[0][1]]["weight"],
    ):
        left, right = edge
        ax.plot(
            [positions[left][0], positions[right][0]],
            [positions[left][1], positions[right][1]],
            color="#6B7280",
            linewidth=width,
            alpha=alpha,
            zorder=1,
        )

    metric_values = [node_metric.get(node, degree.get(node, 1)) for node in graph.nodes]
    node_sizes = _scale([math.sqrt(max(value, 1)) for value in metric_values], size_min, size_max)
    for node, size in zip(graph.nodes, node_sizes):
        cluster = cluster_map.get(node, 1)
        ax.scatter(
            positions[node][0],
            positions[node][1],
            s=size,
            color=PALETTE[(cluster - 1) % len(PALETTE)],
            alpha=0.82,
            edgecolor="white",
            linewidth=0.75,
            zorder=2,
        )

    forced_labels = set(forced_labels or []) & set(graph.nodes)
    label_offsets = label_offsets or {}
    label_alignments = label_alignments or {}
    ranked = sorted(
        graph.nodes,
        key=lambda node: (node_metric.get(node, 0), _display_label(node)),
        reverse=True,
    )
    labeled_nodes = set(ranked[:max_labels]) | forced_labels
    center_x = sum(x for x, _ in positions.values()) / len(positions)
    center_y = sum(y for _, y in positions.values()) / len(positions)
    for node in labeled_nodes:
        x, y = positions[node]
        dx, dy = x - center_x, y - center_y
        norm = math.hypot(dx, dy) or 1.0
        # Place labels just outside nodes and align them away from the panel center.
        label_x = x + 0.16 * dx / norm
        label_y = y + 0.16 * dy / norm
        extra_x, extra_y = label_offsets.get(node, (0.0, 0.0))
        label_x += extra_x
        label_y += extra_y
        default_ha = "left" if dx >= 0 else "right"
        default_va = "bottom" if dy >= 0 else "top"
        ha, va = label_alignments.get(node, (default_ha, default_va))
        ax.annotate(
            _short_label(node, label_width),
            xy=(x, y),
            xytext=(label_x, label_y),
            textcoords="data",
            ha=ha,
            va=va,
            fontsize=font_size,
            family="serif",
            color="#111827",
            bbox={"boxstyle": "round,pad=0.10", "facecolor": "white", "edgecolor": "none", "alpha": 0.90},
            arrowprops={"arrowstyle": "-", "color": "#9CA3AF", "linewidth": 0.35, "alpha": 0.75},
            zorder=3,
            clip_on=False,
        )

    if show_legend:
        handles = [
            mlines.Line2D(
                [],
                [],
                color=PALETTE[(cluster - 1) % len(PALETTE)],
                marker="o",
                linestyle="None",
                markersize=5.4,
                label=f"Cluster {cluster}",
            )
            for cluster in sorted(set(cluster_map.values()))
        ]
        ax.legend(handles=handles, loc="upper right", frameon=False, fontsize=6.8, handletextpad=0.3)
    ax.set_title(title, fontsize=9.3 if compact else 10.3, fontweight="bold", pad=2.5)
    ax.set_axis_off()
    ax.margins(0.16 if compact else 0.13)


def top_items(graph, node_metric, limit=5):
    """Return most influential displayed nodes for use in paper text/CSV, not in the figure body."""
    return sorted(graph.nodes, key=lambda node: (node_metric.get(node, 0), _display_label(node)), reverse=True)[:limit]


def _paper_style():
    apply_plot_style()
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 8,
            "axes.titlesize": 10,
            "legend.fontsize": 7,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _save_direct(fig, stem):
    for directory in (PNG_DIR, PDF_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_DIR / f"{stem}.png", dpi=600, bbox_inches="tight")
    fig.savefig(PDF_DIR / f"{stem}.pdf", bbox_inches="tight")


def create_single_network_figure(graph, cluster_map, node_metric, title, label_width=24):
    _paper_style()
    fig = plt.figure(figsize=(7.16, 4.05))
    ax = fig.add_subplot(111)
    _draw_network_map(ax, graph, cluster_map, node_metric, title, label_width=label_width, max_labels=12)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.90, bottom=0.02)
    return fig


def create_combined_figure(network_specs):
    _paper_style()
    fig = plt.figure(figsize=(7.16, 3.92))
    grid = fig.add_gridspec(1, 3, wspace=0.21)
    for index, spec in enumerate(network_specs):
        ax = fig.add_subplot(grid[0, index])
        _draw_network_map(
            ax,
            spec["graph"],
            spec["clusters"],
            spec["metric"],
            spec["title"],
            label_width=spec["label_width"],
            max_labels=spec.get("max_labels", 6),
            forced_labels=spec.get("forced_labels"),
            label_offsets=spec.get("label_offsets"),
            label_alignments=spec.get("label_alignments"),
            show_legend=False,
            compact=True,
        )
    handles = [
        mlines.Line2D([], [], color=PALETTE[i], marker="o", linestyle="None", markersize=5.2, label=f"Cluster {i + 1}")
        for i in range(3)
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=6.8,
               bbox_to_anchor=(0.5, 0.006), handletextpad=0.3, columnspacing=1.1)
    fig.subplots_adjust(left=0.015, right=0.985, top=0.94, bottom=0.095)
    return fig


def prepare_data():
    data = load_analysis_data()
    cocitation_graph, cocitation_frequency = _cooccurrence_graph(_groups(data["CR"]), top_n=18, min_occurrences=4)
    keyword_graph, keyword_frequency = _cooccurrence_graph(_keyword_groups(data), top_n=18, min_occurrences=4)
    source_graph, source_frequency = _source_coupling_graph(data, top_n=18)

    cocitation_clusters = _detect_communities(cocitation_graph)
    keyword_clusters = _detect_communities(keyword_graph)
    source_clusters = _detect_communities(source_graph)

    centrality = pd.concat(
        [
            _centrality_table(cocitation_graph, "Co-cited references", cocitation_frequency, cocitation_clusters),
            _centrality_table(keyword_graph, "Keyword co-occurrence", keyword_frequency, keyword_clusters),
            _centrality_table(source_graph, "Source bibliographic coupling", source_frequency, source_clusters),
        ],
        ignore_index=True,
    )

    return {
        "cocitation": (cocitation_graph, cocitation_frequency, cocitation_clusters),
        "keywords": (keyword_graph, keyword_frequency, keyword_clusters),
        "sources": (source_graph, source_frequency, source_clusters),
        "centrality": centrality,
    }


if __name__ == "__main__":
    prepared = prepare_data()
    cocitation, cocitation_frequency, cocitation_clusters = prepared["cocitation"]
    keywords, keyword_frequency, keyword_clusters = prepared["keywords"]
    sources, source_frequency, source_clusters = prepared["sources"]
    centrality_data = prepared["centrality"]

    cocitation_metric = dict(cocitation.degree(weight="weight"))
    keyword_metric = {node: keyword_frequency[node] for node in keywords.nodes}
    source_metric = dict(sources.degree(weight="weight"))

    specs = [
        {
            "graph": cocitation,
            "clusters": cocitation_clusters,
            "metric": cocitation_metric,
            "title": "(a) Co-citation",
            "stem": "figure5a_co_citation_network",
            "label_width": 26,
            "max_labels": 0,
            "forced_labels": {
                "DOI 10.1145/3511861.3511863",
                "DOI 10.1145/3501385.3543957",
                "DOI 10.1145/3623762.3633499",
                "DOI 10.1145/3545945.3569759",
                "DOI 10.1145/3568813.3600138",
                "DOI 10.1145/3231711",
                "DOI 10.1145/3293881.3295779",
            },
            "label_offsets": {
                "DOI 10.1145/3231711": (0.45, 0.34),
                "DOI 10.1145/3293881.3295779": (-0.34, -0.20),
            },
        },
        {
            "graph": keywords,
            "clusters": keyword_clusters,
            "metric": keyword_metric,
            "title": "(b) Keyword co-occurrence",
            "stem": "figure5b_keyword_network",
            "label_width": 24,
            "max_labels": 0,
            "forced_labels": {
                "STUDENTS", "PROGRAMMING EDUCATION", "EDUCATION COMPUTING",
                "GENERATIVE AI", "CHATGPT", "CS1", "LANGUAGE MODEL",
            },
            "label_offsets": {
                "PROGRAMMING EDUCATION": (-0.20, 0.18),
                "EDUCATION COMPUTING": (-0.28, 0.10),
                "LANGUAGE MODEL": (0.22, -0.08),
                "STUDENTS": (-0.08, 0.08),
            },
            "label_alignments": {
                "PROGRAMMING EDUCATION": ("right", "bottom"),
                "EDUCATION COMPUTING": ("right", "bottom"),
            },
        },
        {
            "graph": sources,
            "clusters": source_clusters,
            "metric": source_metric,
            "title": "(c) Source coupling",
            "stem": "figure5c_source_coupling_network",
            "label_width": 22,
            "max_labels": 0,
            "forced_labels": {"ACM TOCE", "ITiCSE", "FIE", "IEEE Access", "ACM ICPS", "CHI 2026"},
            "label_offsets": {
                "ACM TOCE": (-0.22, 0.28),
                "ITiCSE": (-0.26, 0.06),
                "FIE": (0.18, 0.22),
                "IEEE Access": (-0.12, -0.10),
                "ACM ICPS": (0.24, -0.06),
                "CHI 2026": (0.24, 0.12),
            },
        },
    ]

    for spec in specs:
        fig = create_single_network_figure(
            spec["graph"],
            spec["clusters"],
            spec["metric"],
            spec["title"],
            spec["label_width"],
        )
        _save_direct(fig, spec["stem"])
        plt.close(fig)

    combined = create_combined_figure(specs)
    _save_direct(combined, "figure5_network_centrality")
    plt.close(combined)
    centrality_data.to_csv(CSV_DIR / "figure5_network_centrality.csv", index=False)
    centrality_data.to_csv(CSV_DIR / "table7_network_centrality.csv", index=False)
