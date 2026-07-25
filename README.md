# Bibliometric

This project generates the figures and tables used in the study from the RData
files in `data/`. It has no web interface. All PNG, PDF, and CSV outputs are
computed by the scripts; no statistical results are hard-coded.

## Running the project

Place the following files in `data/`:

- `Master_Deduplicated.RData`: deduplicated master dataset used for Figure 1(b),
  Figures 2–3, and Tables 3–6.
- `acm.RData`: raw ACM search records used for Figures 1(a) and 1(b).
- `IEEE.RData`: raw IEEE Xplore search records used for Figures 1(a) and 1(b).
- `scopus.RData`: raw Scopus search records used for Figures 1(a) and 1(b).
- `wos.RData`: raw Web of Science search records used for Figures 1(a) and 1(b).

Run the following command from the project root:

```bash
uv run run.py
```

Outputs are saved in:

- PNG figures: `outputs/png/`
- PDF figures: `outputs/pdf/`
- Figure and table data: `outputs/csv/`

The analysis period is controlled by `START_YEAR` and `END_YEAR` in `utils.py`.
It is currently 2016–2026. Only master records whose `PY` value falls within
this range are included in Figures 2–3 and Tables 3–6.

## 1. Master-data fields

The analysis primarily uses these bibliometrix fields:

| Field | Meaning | Use |
| --- | --- | --- |
| `PY` | Publication year | Annual publication and author output |
| `DI` / `DI_norm` | Original/normalized DOI | Database matching, document identification, and Tables 3–4 |
| `TI` / `TI_norm` | Original/normalized title | Database matching when a DOI is unavailable |
| `AU_IN` | Author surname and initials | Author output and author-level bibliographic coupling |
| `AU` | Full author name | Homonym checking in Figure 2(b) and identity separation in Table 4 |
| `SO` | Journal, conference, or other source title | Source output and source-level coupling |
| `SR_FULL` | Full source-reference label | Document display name in Table 4 |
| `RP` | Reprint/corresponding-author address | Corresponding-author country |
| `C1` | Author affiliation address | Country identification when `RP` is missing |
| `CR` | Cited-reference list | Co-citation and bibliographic-coupling analyses |
| `ID` | Keywords Plus/indexed keywords | Keyword co-occurrence and thematic clustering |
| `DE` | Author keywords | Keyword co-occurrence and thematic clustering |
| `DB_SOURCE` | Source database of the master record | Tie-breaking for Figure 1(b) matching conflicts |

DOIs are converted to lowercase and stripped of URL prefixes, `doi:`, and
trailing punctuation. Title matching normalizes case, accents, whitespace, and
punctuation.

## 2. Figure 1(a): Initial records by database

Script: `figures/figure1a.py`  
Output: `outputs/csv/figure1a.csv`

The script reads the four database-specific RData files. Each bar equals the
total number of rows in that file before deduplication. A document found in
multiple databases is counted once in each of those databases.

| Column | Meaning |
| --- | --- |
| `database` | IEEE Xplore, ACM DL, Scopus, or Web of Science |
| `records` | Number of rows in the corresponding raw RData file |

The x-axis shows databases, the y-axis shows `Raw records`, and each bar label
is the corresponding `records` value.

## 3. Figure 1(b): Database overlap after deduplication

Script: `figures/figure1b.py`  
Output: `outputs/csv/figure1b.csv`

Each unique document in `Master_Deduplicated.RData` is assigned to the
databases in which it occurs:

1. Raw records are matched to the master data by normalized DOI.
2. A normalized title is used when the DOI is missing or cannot be matched.
3. `DB_SOURCE` helps select a record when one key matches multiple master rows.
4. Each document receives a database set such as `{ACM}`, `{IEEE, Scopus}`, or
   all four databases.
5. Counts represent exact combinations. For example, `IEEE+Scopus` excludes
   documents also found in ACM or Web of Science.
6. The script reconstructs the marginal database totals from the overlap
   combinations and stops if they do not equal the raw-file row counts.

| Column | Meaning |
| --- | --- |
| `database_combination` | Exact database combination; for example, `ACM only` or `All four` |
| `records` | Number of deduplicated documents in that exact combination |
| `number_of_databases` | Number of databases in the combination (1–4) |

## 4. Figure 2(a): Annual publication output

Script: `figures/figure2a.py`  
Output: `outputs/csv/figure2a.csv`

The master data are filtered to the analysis period and grouped by `PY`. Years
with no documents are retained with a count of zero.

| Column | Meaning |
| --- | --- |
| `year` | Publication year from `PY` |
| `records` | Number of deduplicated documents published in that year |

## 5. Figure 2(b): Annual output of the most productive authors

Script: `figures/figure2b.py`  
Output: `outputs/csv/figure2b.csv`  
Homonym audit: `outputs/csv/figure2b_excluded_ambiguous_authors.csv`

1. Author abbreviations are read from `AU_IN`; an author is counted at most
   once per document.
2. Output is accumulated by author and year.
3. Positional matches between `AU_IN` and `AU` are used to check abbreviations
   against full names.
4. Case, accents, LaTeX accents, hyphens, and middle-name formats are
   normalized. For example, `ERICSON BARBARA J` and
   `ERICSON BARBARA JANE` are treated as name-format variants.
5. An abbreviation mapped to two or more incompatible full names is excluded
   because its output cannot reliably be assigned to one person.
6. `NA NA` is excluded as invalid. A missing full-name mapping alone does not
   imply a homonym.
7. The top ten authors are selected after confirmed homonyms are excluded.

This procedure cannot distinguish different people who have exactly the same
full name in the available data.

| Figure CSV column | Meaning |
| --- | --- |
| `author` | Author abbreviation from `AU_IN` |
| `year` | Publication year |
| `records` | Deduplicated documents involving the author in that year |
| `total` | Author's total documents over the full analysis period |

| Audit CSV column | Meaning |
| --- | --- |
| `author` | Excluded author abbreviation |
| `records` | Documents that would have been merged without exclusion |
| `matched_full_names` | Full names matched from `AU`, with their frequencies |
| `reason` | Reason for exclusion |

## 6. Figure 3(a): Most productive publication sources

Script: `figures/figure3a.py`  
Output: `outputs/csv/figure3a.csv`

The script cleans whitespace and minor field fragments in `SO`, counts
documents by source, and selects the top ten sources.

| Column | Meaning |
| --- | --- |
| `source` | Full cleaned journal, conference, or publication-source name |
| `records` | Number of deduplicated documents published by that source |

Long names are shortened only in the figure; the CSV retains full names.

## 7. Figure 3(b): Corresponding-author countries

Script: `figures/figure3b.py`  
Output: `outputs/csv/figure3b.csv`

Country is identified from `RP`, or from the first `C1` affiliation when `RP`
is missing. Common variants are standardized (for example, `USA`/`United
States` and `England`/`United Kingdom`). Unidentified countries are excluded,
and the top ten countries are retained.

| Column | Meaning |
| --- | --- |
| `country` | Standardized corresponding-author country |
| `records` | Deduplicated documents assigned to that country; at most one country per document |

## 8. Table 1: Search strategy

Output: `outputs/csv/table1_search_strategy.csv`

This table describes search concepts rather than document-level observations,
so it has no DOI column.

| Column | Meaning |
| --- | --- |
| `category` | Search-concept category |
| `keywords` | Semicolon-separated search terms in the category |
| `reason` | Purpose of including the category in the query |

## 9. Table 2: Bibliometric indicators

Output: `outputs/csv/table2_indicators.csv`

This table defines the analysis indicators and is not document-level data.

| Column | Meaning |
| --- | --- |
| `indicator` | Indicator name |
| `operationalization` | Exact counting rule used by this project |

## 10. Table 3: Co-cited references

Output: `outputs/csv/table3_cocited_references.csv`

Two references are co-cited when the same master document cites both. The
unique references in each `CR` list are connected pairwise. The table reports
the ten references with the highest weighted degree.

If a reference occurs in a document containing \(m\) unique references, it
gains \(m-1\) weighted connections from that document. Summing across all
master documents gives `raw_degree`.

| Column | Meaning |
| --- | --- |
| `reference_name` | Readable reference, usually including first author, year, title, and source |
| `doi` | Normalized DOI, obtained from the master RData or supplemented from Crossref |
| `metadata_source` | `RData file`, `Crossref DOI API`, or `Unavailable` |
| `raw_degree` | Sum of weighted co-citation connections to other references |
| `degree` | Normalized weighted degree: `raw_degree / maximum raw_degree among all references` |
| `occurrences` | Number of master documents containing the reference, counted once per document |
| `degree_definition` | Text definition of the `raw_degree` network measure |
| `degree_calculation` | Text description of the `degree` normalization formula |

### Degree example for co-citation

Suppose document D1 cites references A, B, and C, while D2 cites A and B:

- D1 creates the pairs A–B, A–C, and B–C. Therefore, A gains 2, B gains 2,
  and C gains 2 in `raw_degree`.
- D2 creates one additional A–B pair. A and B each gain 1.
- The final `raw_degree` values are A = 3, B = 3, and C = 2.
- Because the maximum is 3, the normalized `degree` values are A = 1.00,
  B = 1.00, and C = 2/3 = 0.67.

Thus, `degree` is a relative score between 0 and 1, not a count. A score of
1 identifies the strongest node in that network. `occurrences` is different:
A occurs in two documents, but its `raw_degree` is 3 because it forms three
weighted co-citation connections.

## 11. Table 4: Bibliographic coupling

Output: `outputs/csv/table4_bibliographic_coupling.csv`  
Author-homonym audit: `outputs/csv/table4_homonymous_authors.csv`

Two entities are bibliographically coupled when they cite the same reference.
Three entity types are calculated separately:

- `Documents`: individual master documents.
- `Authors`: the union of references from all documents by an author.
- `Sources`: the union of references from all documents in a source.

For author homonyms, positional `AU_IN`–`AU` matches are normalized for case,
accents, German `ß`, LaTeX accents, hyphens, and middle-name formats. Compatible
variants such as `PAASSEN` and `PAAßEN` are merged. Incompatible full names
sharing an abbreviation are split into independent author nodes. All split
nodes participate in the network; only the highest-`raw_degree` identity in
each homonym group can enter the global top ten. Ties are resolved by number of
references and then alphabetically. Ambiguous records that cannot be assigned
reliably are not assigned to any identity in that homonym group.

If \(k\) entities cite a particular reference, each receives \(k-1\) connection
weight from that reference. These weights are summed into `raw_degree`.

| Column | Meaning |
| --- | --- |
| `unit` | `Documents`, `Authors`, or `Sources` |
| `item` | Entity label |
| `full_name` | Full author name for author rows, otherwise blank |
| `doi` | DOI for document rows when available, otherwise blank |
| `raw_degree` | Sum of weighted coupling connections created by shared references |
| `degree` | `raw_degree / maximum raw_degree within the same unit` |
| `references` | Number of unique references belonging to the entity |
| `degree_definition` | Definition of `raw_degree` |
| `degree_calculation` | Description of the normalization formula |

### Degree example for bibliographic coupling

Suppose documents X, Y, and Z cite the following references:

- X cites R1 and R2.
- Y cites R1 and R3.
- Z cites R1 and R2.

R1 is shared by three documents, so it contributes \(3-1=2\) to each
document. R2 is shared by X and Z, so it contributes 1 to each. R3 is cited
only by Y and contributes no coupling connection. The resulting
`raw_degree` values are X = 3, Y = 2, and Z = 3. The maximum is 3, so
`degree` is X = 1.00, Y = 0.67, and Z = 1.00.

Having more `references` does not necessarily produce a higher `degree`; only
references shared with other entities create coupling connections.

The homonym-audit CSV contains:

| Column | Meaning |
| --- | --- |
| `author` | Ambiguous author abbreviation |
| `full_name` | One independently analyzed identity mapped to that abbreviation |
| `raw_degree` | Weighted coupling degree of that identity |
| `degree` | Normalized degree using the maximum across all full-name author nodes |
| `references` | Unique references assigned to the identity |
| `highest_in_homonym_group` | Whether this identity ranks first within its abbreviation group |
| `entered_table4_top10` | Whether the group's winning identity entered the global author top ten |

## 12. Table 5: Keyword co-occurrence

Output: `outputs/csv/table5_keyword_cooccurrence.csv`

`ID` indexed keywords and `DE` author keywords are analyzed separately.
Different keywords in one document are connected pairwise, with each keyword
counted at most once per document. The top ten keywords by weighted degree are
reported for each vocabulary.

| Column | Meaning |
| --- | --- |
| `vocabulary` | `Indexed keywords` (`ID`) or `Author keywords` (`DE`) |
| `item` | Normalized keyword |
| `raw_degree` | Sum of weighted co-occurrence connections to other keywords |
| `degree` | `raw_degree / maximum raw_degree within the same vocabulary` |
| `occurrences` | Number of documents containing the keyword |
| `degree_definition` | Definition of `raw_degree` |
| `degree_calculation` | Description of the normalization formula |

For example, if one document contains the keywords `AI`, `feedback`, and
`learning`, each keyword gains 2 in `raw_degree`. If another document contains
`AI` and `feedback`, those two keywords each gain 1 more. Their final
`raw_degree` values are therefore 3, 3, and 2. After division by the maximum
value of 3, their `degree` values are 1.00, 1.00, and 0.67.

Rows aggregate multiple documents and therefore do not have a single DOI.

## 13. Table 6: Thematic clusters

Output: `outputs/csv/table6_thematic_clusters.csv`

The thematic clusters are built from keyword co-occurrence networks:

1. `ID` and `DE` are processed separately.
2. Each vocabulary retains at most the 250 most frequent terms, and terms must
   occur in at least two documents.
3. Keyword pairs in a document create edges; each co-occurrence adds 1 to the
   edge weight.
4. Isolated keywords are removed.
5. NetworkX Louvain community detection uses co-occurrence weights and a fixed
   random seed of 42.
6. Up to five indexed-keyword communities and four author-keyword communities
   are reported.
7. The five leading terms in each community are selected by weighted degree,
   occurrence frequency, and name.

| Column | Meaning |
| --- | --- |
| `vocabulary` | `Indexed keywords` or `Author keywords` |
| `cluster_label` | Highest-weighted-degree keyword in the community; an automatically generated label |
| `terms` | Number of keywords in the community |
| `representative_terms` | Five leading keywords, separated by semicolons |

Clusters aggregate multiple documents and therefore do not have a single DOI.

## 14. Analysis summary

Output: `outputs/csv/analysis_summary.csv`

| Column | Meaning |
| --- | --- |
| `metric` | Summary-metric name |
| `value` | Metric value |
| `analysis_records` | Deduplicated master documents in the analysis period |
| `cited_reference_occurrences` | Sum of unique cited references per master document |
| `unique_cited_references` | Number of distinct cited references across all `CR` fields |
| `unique_authors` | Distinct author identities with at least one usable coupling reference |
| `unique_sources` | Distinct sources with at least one usable coupling reference |

This file is a run-level validation summary and does not correspond to an
individual document.

## 15. DOI rules

- A DOI is supplied whenever a row represents one identifiable document.
  Currently, this applies to Table 3 reference rows and Table 4 document rows.
- A single DOI is not supplied for rows aggregating authors, sources, keywords,
  themes, or other groups of documents.
- Crossref DOI metadata are cached in `data/doi_metadata_cache.csv` for reuse.

## 16. Project structure

```text
Bibliometric/
├── README.md              # Project setup, methodology, and output documentation
├── pyproject.toml         # Python version, package metadata, and dependencies
├── uv.lock                # Exact dependency versions used for reproducible installation
├── .python-version        # Python version selected by uv and compatible version managers
├── run.py                 # Main entry point; runs every figure script and then tables.py
├── tables.py              # Generates Tables 1–6 and the analysis-summary CSV
├── utils.py               # Shared data loading, cleaning, year filtering, plotting, and file-saving utilities
├── data/
│   ├── Master_Deduplicated.RData  # Deduplicated master records used in the main analyses
│   ├── acm.RData                  # Raw ACM records used in the database-count and overlap figures
│   ├── IEEE.RData                 # Raw IEEE Xplore records used in the database-count and overlap figures
│   ├── scopus.RData               # Raw Scopus records used in the database-count and overlap figures
│   ├── wos.RData                  # Raw Web of Science records used in the database-count and overlap figures
│   └── doi_metadata_cache.csv     # Reusable Crossref metadata cache, created when DOI lookups are needed
├── figures/
│   ├── figure1a.py        # Counts raw records in each source database and draws Figure 1(a)
│   ├── figure1b.py        # Matches deduplicated records across databases and draws the overlap in Figure 1(b)
│   ├── figure2a.py        # Calculates and plots annual publication output for Figure 2(a)
│   ├── figure2b.py        # Ranks authors, audits ambiguous names, and plots annual author output for Figure 2(b)
│   ├── figure3a.py        # Ranks publication sources and draws Figure 3(a)
│   └── figure3b.py        # Identifies corresponding-author countries and draws Figure 3(b)
└── outputs/
    ├── README.md          # Short guide linking to the complete output documentation
    ├── png/               # Generated high-resolution PNG figures
    ├── pdf/               # Generated vector PDF figures
    └── csv/               # Generated plotting data, tables, audits, and summary statistics
```

The `.bib` files in `data/` are the original database exports retained for
provenance. The current analysis scripts read the corresponding `.RData` files.
The `.venv/`, `__pycache__/`, and `.DS_Store` entries are local environment,
Python cache, and macOS metadata files, respectively; they are not project
inputs and are omitted from the structure above.

`run.py` executes the figure scripts in numerical order and then runs
`tables.py`. Each figure script prepares its own data, draws the figure, and
writes the corresponding PNG, PDF, and CSV files.
