from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
import re
import unicodedata
from urllib.parse import quote

import networkx as nx
import pandas as pd
import requests

from utils import CSV_DIR, PROJECT_ROOT, load_analysis_data, normalize_doi, normalize_source, split_terms


DOI_CACHE_FILE = PROJECT_ROOT / "data" / "doi_metadata_cache.csv"


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip(" ,.;").upper()


def _groups(series: pd.Series) -> list[list[str]]:
    return [[_clean(x) for x in split_terms(value) if _clean(x)] for value in series]


def _split_author_names(value: object) -> list[str]:
    if pd.isna(value):
        return []
    return [
        re.sub(r"\s+", " ", item).strip(" ,.;")
        for item in str(value).split(";")
        if item.strip(" ,.;")
    ]


def _author_signature(full_name: str) -> str:
    """Merge only obvious formatting variants of the same complete author name."""
    text = re.sub(r"\\[A-Za-z]+\{([^{}]+)\}", r"\1", full_name)
    text = re.sub(r"\\[`'^\"~=]\{?([A-Za-z])\}?", r"\1", text)
    text = re.sub(r"\\[RVrv](?=[A-Za-z])", "", text)
    text = text.replace("{", "").replace("}", "")
    text = unicodedata.normalize("NFKD", text.upper()).encode("ascii", "ignore").decode()
    tokens = re.findall(r"[A-Z]+", text)
    if len(tokens) < 2:
        return ""
    surname, given = tokens[0], tokens[1:]
    return "|".join([surname, given[0], "".join(token[0] for token in given[1:])])


def _author_identity_data(data: pd.DataFrame) -> dict[str, dict[str, str]]:
    """Map each author initial form and identity signature to a display name."""
    complete_names = defaultdict(lambda: defaultdict(Counter))
    for row in data[["AU_IN", "AU"]].itertuples(index=False):
        initials = _split_author_names(row.AU_IN)
        names = _split_author_names(row.AU)
        if len(initials) != len(names):
            continue
        for initial_name, complete_name in zip(initials, names):
            author = _clean(initial_name)
            signature = _author_signature(complete_name)
            if signature:
                complete_names[author][signature][complete_name] += 1

    return {
        author: {
            signature: name_counts.most_common(1)[0][0]
            for signature, name_counts in identities.items()
        }
        for author, identities in complete_names.items()
    }


def _normalized_degree_from_groups(groups: list[list[str]]) -> tuple[Counter, Counter]:
    degree = Counter()
    frequency = Counter()
    for group in groups:
        members = list(dict.fromkeys(group))
        frequency.update(members)
        for member in members:
            degree[member] += max(0, len(members) - 1)
    return degree, frequency


def _rank(degree: Counter, frequency: Counter, top_n: int = 10) -> pd.DataFrame:
    maximum = max(degree.values(), default=1)
    rows = [
        {
            "item": item,
            "raw_degree": value,
            "degree": value / maximum,
            "occurrences": frequency[item],
        }
        for item, value in degree.most_common(top_n)
    ]
    return pd.DataFrame(rows)


def _reference_metadata(data: pd.DataFrame) -> dict[str, dict[str, str]]:
    """Map DOI values to readable references using only the master RData."""
    metadata = {}
    for row in data.itertuples(index=False):
        doi = normalize_doi(getattr(row, "DI_norm", None))
        if not doi:
            doi = normalize_doi(getattr(row, "DI", None))
        if not doi:
            continue
        authors = split_terms(getattr(row, "AU_IN", None))
        first_author = authors[0].title() if authors else "Unknown author"
        year = str(getattr(row, "PY", "")).replace(".0", "")
        raw_title = getattr(row, "TI_raw", None)
        title = str(raw_title if pd.notna(raw_title) else getattr(row, "TI", "Untitled"))
        source = str(getattr(row, "SO", "")).title()
        key = doi
        metadata[key] = {
            "reference_name": f"{first_author}, {year}, {title}, {source}",
            "doi": key,
            "metadata_source": "RData file",
        }
    return metadata


def _load_doi_cache() -> dict[str, dict[str, str]]:
    if not DOI_CACHE_FILE.exists():
        return {}
    cache = pd.read_csv(DOI_CACHE_FILE).fillna("")
    return {str(row["doi"]).lower(): row.to_dict() for _, row in cache.iterrows()}


def _save_doi_cache(cache: dict[str, dict[str, str]]) -> None:
    if cache:
        pd.DataFrame(cache.values()).sort_values("doi").to_csv(DOI_CACHE_FILE, index=False)


def _fetch_crossref(doi: str) -> dict[str, str] | None:
    try:
        response = requests.get(
            f"https://api.crossref.org/works/{quote(doi, safe='')}",
            timeout=15,
            headers={"User-Agent": "BibliometricReplication/0.1"},
        )
        response.raise_for_status()
        message = response.json()["message"]
    except (requests.RequestException, KeyError, ValueError):
        return None

    authors = message.get("author", [])
    first_author = (authors[0].get("family") or authors[0].get("name")) if authors else "Unknown author"
    date_parts = message.get("issued", {}).get("date-parts", [[""]])
    year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
    title = (message.get("title") or ["Untitled"])[0]
    source = (message.get("container-title") or [message.get("publisher", "")])[0]
    return {
        "reference_name": f"{first_author}, {year}, {title}, {source}",
        "doi": doi,
        "metadata_source": "Crossref DOI API",
    }


def _supplement_doi_metadata(
    metadata: dict[str, dict[str, str]], references: pd.Series
) -> dict[str, dict[str, str]]:
    cache = _load_doi_cache()
    for reference in references:
        match = re.search(r"\b10\.\d{4,9}/\S+", str(reference), flags=re.IGNORECASE)
        if not match:
            continue
        doi = match.group(0).rstrip(".,;").lower()
        if doi in metadata:
            continue
        if doi not in cache:
            fetched = _fetch_crossref(doi)
            if fetched:
                cache[doi] = fetched
        if doi in cache:
            metadata[doi] = cache[doi]
    _save_doi_cache(cache)
    return metadata


def _readable_reference(reference: str, metadata: dict[str, dict[str, str]]) -> dict[str, str]:
    doi_match = re.search(r"\b10\.\d{4,9}/\S+", reference, flags=re.IGNORECASE)
    if not doi_match:
        return {
            "reference_name": reference.title(),
            "doi": "",
            "metadata_source": "RData file",
        }
    doi = doi_match.group(0).rstrip(".,;").lower()
    return metadata.get(
        doi,
        {
            "reference_name": f"Title unavailable from DOI metadata ({doi})",
            "doi": doi,
            "metadata_source": "Unavailable",
        },
    )


def _coupling_degree(entity_references: dict[str, set[str]]) -> Counter:
    reference_entities = defaultdict(set)
    for entity, references in entity_references.items():
        for reference in references:
            reference_entities[reference].add(entity)
    degree = Counter()
    for entities in reference_entities.values():
        size = len(entities)
        for entity in entities:
            degree[entity] += max(0, size - 1)
    return degree


def _coupling_table(
    entity_references: dict[str, set[str]],
    labels: dict[str, str],
    unit: str,
    dois: dict[str, str] | None = None,
    full_names: dict[str, str] | None = None,
) -> pd.DataFrame:
    degree = _coupling_degree(entity_references)
    maximum = max(degree.values(), default=1)
    rows = []
    for entity, value in degree.most_common(10):
        rows.append(
            {
                "unit": unit,
                "item": labels.get(entity, entity),
                "full_name": (full_names or {}).get(entity, ""),
                "doi": (dois or {}).get(entity, ""),
                "raw_degree": value,
                "degree": value / maximum,
                "references": len(entity_references[entity]),
                "degree_definition": "Weighted bibliographic-coupling degree: total shared-reference connection weight for the entity.",
                "degree_calculation": "degree = raw_degree / maximum raw_degree within the same unit of analysis.",
            }
        )
    return pd.DataFrame(rows)


def _author_coupling_table(
    entity_references: dict[str, set[str]],
    initials: dict[str, str],
    full_names: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rank only the strongest complete-name identity for each initial form."""
    degree = _coupling_degree(entity_references)
    maximum = max(degree.values(), default=1)
    rows = [
        {
            "_entity": entity,
            "unit": "Authors",
            "item": initials[entity],
            "full_name": full_names.get(entity, ""),
            "doi": "",
            "raw_degree": value,
            "degree": value / maximum,
            "references": len(entity_references[entity]),
            "degree_definition": "Weighted bibliographic-coupling degree: total shared-reference connection weight for the entity.",
            "degree_calculation": "degree = raw_degree / maximum raw_degree within the same unit of analysis.",
        }
        for entity, value in degree.items()
    ]
    ranked = pd.DataFrame(rows).sort_values(
        ["raw_degree", "references", "full_name"],
        ascending=[False, False, True],
    )

    # Every complete-name identity participates in the network calculation, but
    # only the highest-scoring identity under a shared initial form can compete
    # for a place in the displayed top 10.
    candidates = ranked.drop_duplicates("item", keep="first")
    table = candidates.head(10).copy()
    table_entities = set(table["_entity"])

    identity_counts = ranked.groupby("item")["_entity"].transform("nunique")
    homonyms = ranked[identity_counts > 1].copy()
    selected_entities = set(candidates["_entity"])
    homonyms["highest_in_homonym_group"] = homonyms["_entity"].isin(selected_entities)
    homonyms["entered_table4_top10"] = homonyms["_entity"].isin(table_entities)
    audit = homonyms.rename(columns={"item": "author"})[
        [
            "author",
            "full_name",
            "raw_degree",
            "degree",
            "references",
            "highest_in_homonym_group",
            "entered_table4_top10",
        ]
    ]
    return table.drop(columns="_entity"), audit


def _thematic_clusters(groups: list[list[str]], vocabulary: str, limit: int) -> pd.DataFrame:
    frequency = Counter(term for group in groups for term in set(group))
    selected = {term for term, count in frequency.most_common(250) if count >= 2}
    graph = nx.Graph()
    graph.add_nodes_from(selected)
    for group in groups:
        terms = sorted(set(group) & selected)
        for left, right in combinations(terms, 2):
            if graph.has_edge(left, right):
                graph[left][right]["weight"] += 1
            else:
                graph.add_edge(left, right, weight=1)
    graph.remove_nodes_from(list(nx.isolates(graph)))
    if not graph:
        return pd.DataFrame(columns=["vocabulary", "cluster_label", "terms", "representative_terms"])
    communities = nx.community.louvain_communities(graph, weight="weight", seed=42)
    communities = sorted(communities, key=len, reverse=True)[:limit]
    weighted_degree = dict(graph.degree(weight="weight"))
    rows = []
    for community in communities:
        representatives = sorted(
            community,
            key=lambda term: (weighted_degree.get(term, 0), frequency[term], term),
            reverse=True,
        )[:5]
        rows.append(
            {
                "vocabulary": vocabulary,
                "cluster_label": representatives[0].title(),
                "terms": len(community),
                "representative_terms": "; ".join(x.title() for x in representatives),
            }
        )
    return pd.DataFrame(rows)


def create_tables() -> None:
    data = load_analysis_data().reset_index(drop=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    table1 = pd.DataFrame(
        [
            ("Domain", "Programming education; introductory programming; novice programmer; computer science education", "Defines the computing-education boundary."),
            ("AI systems", "Multi-agent; large language model; LLM; generative AI; retrieval-augmented generation; AI tutor; intelligent tutoring system", "Captures AI, LLM, and tutor tools used by learners."),
            ("Scaffolding", "Scaffolding; adaptive learning; adaptive scaffolding; dynamic scaffolding; scaffolding fading; cognitive load", "Captures support and feedback mechanisms."),
            ("Representation", "Representation form; syntax feedback; syntax hints; syntax error; logic diagram; pseudocode; code template", "Captures code, diagram, hint, and representation issues."),
        ],
        columns=["category", "keywords", "reason"],
    )
    table1.to_csv(CSV_DIR / "table1_search_strategy.csv", index=False)

    table2 = pd.DataFrame(
        [
            ("TP", "Total unique publications in the analysis period."),
            ("Annual production", "Publication records grouped by year."),
            ("Database coverage", "Source-database presence and available overlap combinations."),
            ("Author productivity", "Number of records associated with each author."),
            ("Country output", "Corresponding-author country count derived from RP, with C1 fallback."),
            ("Source productivity", "Number of records by publication source."),
            ("Thematic frequency", "Author and indexed keyword occurrence counts."),
        ],
        columns=["indicator", "operationalization"],
    )
    table2.to_csv(CSV_DIR / "table2_indicators.csv", index=False)

    reference_groups = _groups(data["CR"])
    ref_degree, ref_frequency = _normalized_degree_from_groups(reference_groups)
    table3 = _rank(ref_degree, ref_frequency)
    metadata = _reference_metadata(data)
    metadata = _supplement_doi_metadata(metadata, table3["item"])
    readable = table3["item"].map(lambda value: _readable_reference(value, metadata)).apply(pd.Series)
    table3 = pd.concat([readable, table3], axis=1)
    table3 = table3.drop(columns="item")
    table3["degree_definition"] = "Weighted co-citation degree: sum of co-citation edge weights connected to the reference."
    table3["degree_calculation"] = "degree = raw_degree / maximum raw_degree in the full cited-reference co-citation network."
    table3.to_csv(CSV_DIR / "table3_cocited_references.csv", index=False)

    document_refs = {}
    document_labels = {}
    document_dois = {}
    author_identities = _author_identity_data(data)
    author_refs = defaultdict(set)
    author_initials = {}
    author_full_names = {}
    source_refs = defaultdict(set)
    for index, row in data.iterrows():
        references = set(reference_groups[index])
        if not references:
            continue
        document_id = f"DOC-{index + 1}"
        document_refs[document_id] = references
        label = row.get("SR_FULL") if pd.notna(row.get("SR_FULL")) else row.get("TI")
        document_labels[document_id] = str(label)
        document_doi = normalize_doi(row.get("DI_norm"))
        document_dois[document_id] = document_doi or normalize_doi(row.get("DI"))

        initials = _split_author_names(row.get("AU_IN"))
        names = _split_author_names(row.get("AU"))
        if len(initials) == len(names):
            for initial_name, complete_name in zip(initials, names):
                author = _clean(initial_name)
                if author == "NA NA":
                    continue
                signature = _author_signature(complete_name)
                if not signature:
                    continue
                entity = f"{author}\x1f{signature}"
                author_refs[entity].update(references)
                author_initials[entity] = author
                author_full_names[entity] = author_identities.get(author, {}).get(
                    signature, complete_name
                )
        else:
            for initial_name in dict.fromkeys(initials):
                author = _clean(initial_name)
                identities = author_identities.get(author, {})
                if author == "NA NA" or len(identities) != 1:
                    continue
                signature, complete_name = next(iter(identities.items()))
                entity = f"{author}\x1f{signature}"
                author_refs[entity].update(references)
                author_initials[entity] = author
                author_full_names[entity] = complete_name

        source = normalize_source(row.get("SO"))
        if source:
            source_refs[_clean(source)].update(references)

    author_table, author_audit = _author_coupling_table(
        dict(author_refs), author_initials, author_full_names
    )
    author_audit.to_csv(CSV_DIR / "table4_homonymous_authors.csv", index=False)
    table4 = pd.concat(
        [
            _coupling_table(document_refs, document_labels, "Documents", document_dois),
            author_table,
            _coupling_table(dict(source_refs), {}, "Sources"),
        ],
        ignore_index=True,
    )
    table4.to_csv(CSV_DIR / "table4_bibliographic_coupling.csv", index=False)

    keyword_tables = []
    thematic_tables = []
    for field, label, cluster_limit in [("ID", "Indexed keywords", 5), ("DE", "Author keywords", 4)]:
        groups = _groups(data[field])
        degree, frequency = _normalized_degree_from_groups(groups)
        ranked = _rank(degree, frequency)
        ranked.insert(0, "vocabulary", label)
        ranked["degree_definition"] = "Weighted keyword co-occurrence degree: sum of co-occurrence edge weights connected to the keyword."
        ranked["degree_calculation"] = "degree = raw_degree / maximum raw_degree within the same keyword vocabulary."
        keyword_tables.append(ranked)
        thematic_tables.append(_thematic_clusters(groups, label, cluster_limit))
    pd.concat(keyword_tables, ignore_index=True).to_csv(CSV_DIR / "table5_keyword_cooccurrence.csv", index=False)
    pd.concat(thematic_tables, ignore_index=True).to_csv(CSV_DIR / "table6_thematic_clusters.csv", index=False)

    summary = pd.DataFrame(
        [
            ("analysis_records", len(data)),
            ("cited_reference_occurrences", sum(len(group) for group in reference_groups)),
            ("unique_cited_references", len(ref_frequency)),
            ("unique_authors", len(author_refs)),
            ("unique_sources", len(source_refs)),
        ],
        columns=["metric", "value"],
    )
    summary.to_csv(CSV_DIR / "analysis_summary.csv", index=False)


if __name__ == "__main__":
    create_tables()
