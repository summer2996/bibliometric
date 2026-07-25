from __future__ import annotations

import re
import unicodedata
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import rdata


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
PNG_DIR = PROJECT_ROOT / "outputs" / "png"
PDF_DIR = PROJECT_ROOT / "outputs" / "pdf"
CSV_DIR = PROJECT_ROOT / "outputs" / "csv"
START_YEAR = 2016
END_YEAR = 2026


def load_master_data() -> pd.DataFrame:
    """Load Master_Deduplicated.RData, or the newest RData as a fallback."""
    preferred = DATA_DIR / "Master_Deduplicated.RData"
    if preferred.exists():
        return load_rdata_frame(preferred)

    files = sorted(DATA_DIR.glob("*.RData"), key=lambda path: path.stat().st_mtime)
    if not files:
        raise FileNotFoundError("Place an .RData file in the data directory before running run.py.")
    return load_rdata_frame(files[-1])


def load_rdata_frame(path: Path) -> pd.DataFrame:
    """Read a bibliometrix RData file as a pandas DataFrame."""
    print(f"Using data file: {path.name}")
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message='Missing constructor for R class "bibliometrixDB"')
        objects = rdata.read_rda(path)
    if "master_records" in objects:
        return objects["master_records"].copy()

    dataframes = {name: value for name, value in objects.items() if isinstance(value, pd.DataFrame)}
    if not dataframes:
        raise ValueError(f"No DataFrame was found in {path.name}.")
    return max(dataframes.values(), key=len).copy()


def load_database_data(filename: str) -> pd.DataFrame:
    """Load a specifically named database RData file, case-insensitively."""
    matches = [path for path in DATA_DIR.glob("*.RData") if path.name.lower() == filename.lower()]
    if not matches:
        raise FileNotFoundError(f"Required data file is missing: data/{filename}")
    return load_rdata_frame(matches[0])


def normalize_doi(value: object) -> str:
    if pd.isna(value):
        return ""
    doi = str(value).lower().strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.strip(" .;,")


def normalize_title(value: object) -> str:
    if pd.isna(value):
        return ""
    title = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", title).strip()


def load_analysis_data() -> pd.DataFrame:
    """Return records within the paper's stated 2019-2026 scope."""
    data = load_master_data()
    data["PY"] = pd.to_numeric(data["PY"], errors="coerce")
    return data[data["PY"].between(START_YEAR, END_YEAR)].copy()


def split_terms(value: object) -> list[str]:
    """Split a semicolon-delimited bibliographic field into clean terms."""
    if pd.isna(value):
        return []
    terms = []
    for term in str(value).split(";"):
        clean = re.sub(r"\s+", " ", term).strip(" ,.;")
        if clean:
            terms.append(clean)
    return list(dict.fromkeys(terms))


def save_figure(fig: plt.Figure, data: pd.DataFrame, stem: str) -> None:
    """Save a figure as PNG/PDF and its plotting data as CSV."""
    for directory in (PNG_DIR, PDF_DIR, CSV_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(PDF_DIR / f"{stem}.pdf", bbox_inches="tight")
    data.to_csv(CSV_DIR / f"{stem}.csv", index=False)


def apply_plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#999999",
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.alpha": 0.22,
            "grid.linewidth": 0.6,
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
        }
    )


COUNTRY_PATTERNS = [
    ("USA", r"\bUSA\b|\bUNITED STATES(?: OF AMERICA)?\b"),
    ("China", r"\bPEOPLES R CHINA\b|\bP\. ?R\. ?CHINA\b|\bCHINA\b"),
    ("United Kingdom", r"\bUNITED KINGDOM\b|\bENGLAND\b|\bSCOTLAND\b|\bWALES\b|\bNORTHERN IRELAND\b|\bUK\b"),
    ("South Korea", r"\bSOUTH KOREA\b|\bREPUBLIC OF KOREA\b|\bKOREA\b"),
    ("Germany", r"\bGERMANY\b"),
    ("Canada", r"\bCANADA\b"),
    ("Finland", r"\bFINLAND\b"),
    ("Australia", r"\bAUSTRALIA\b"),
    ("India", r"\bINDIA\b"),
    ("Japan", r"\bJAPAN\b"),
    ("Brazil", r"\bBRAZIL\b"),
    ("Spain", r"\bSPAIN\b"),
    ("Italy", r"\bITALY\b"),
    ("France", r"\bFRANCE\b"),
    ("Netherlands", r"\bNETHERLANDS\b"),
    ("Sweden", r"\bSWEDEN\b"),
    ("Norway", r"\bNORWAY\b"),
    ("Denmark", r"\bDENMARK\b"),
    ("Switzerland", r"\bSWITZERLAND\b"),
    ("Austria", r"\bAUSTRIA\b"),
    ("Belgium", r"\bBELGIUM\b"),
    ("Portugal", r"\bPORTUGAL\b"),
    ("Ireland", r"\bIRELAND\b"),
    ("New Zealand", r"\bNEW ZEALAND\b"),
    ("Singapore", r"\bSINGAPORE\b"),
    ("Malaysia", r"\bMALAYSIA\b"),
    ("Indonesia", r"\bINDONESIA\b"),
    ("Taiwan", r"\bTAIWAN\b"),
    ("Hong Kong", r"\bHONG KONG\b"),
    ("Türkiye", r"\bTURKEY\b|\bTURKIYE\b|\bTÜRKIYE\b"),
    ("Israel", r"\bISRAEL\b"),
    ("Saudi Arabia", r"\bSAUDI ARABIA\b"),
    ("United Arab Emirates", r"\bUNITED ARAB EMIRATES\b|\bU ARAB EMIRATES\b|\bUAE\b"),
    ("South Africa", r"\bSOUTH AFRICA\b"),
    ("Mexico", r"\bMEXICO\b"),
    ("Chile", r"\bCHILE\b"),
    ("Colombia", r"\bCOLOMBIA\b"),
    ("Argentina", r"\bARGENTINA\b"),
    ("Poland", r"\bPOLAND\b"),
    ("Czechia", r"\bCZECH REPUBLIC\b|\bCZECHIA\b"),
    ("Greece", r"\bGREECE\b"),
    ("Romania", r"\bROMANIA\b"),
    ("Russia", r"\bRUSSIA\b|\bRUSSIAN FEDERATION\b"),
    ("Pakistan", r"\bPAKISTAN\b"),
    ("Bangladesh", r"\bBANGLADESH\b"),
    ("Thailand", r"\bTHAILAND\b"),
    ("Vietnam", r"\bVIETNAM\b|\bVIET NAM\b"),
]


def extract_country(row: pd.Series) -> str | None:
    """Extract the corresponding-author country, falling back to C1."""
    address = row.get("RP")
    if pd.isna(address) or not str(address).strip():
        address = row.get("C1")
        if pd.notna(address):
            address = str(address).split(";")[0]
    if pd.isna(address):
        return None
    text = str(address).upper()
    for country, pattern in COUNTRY_PATTERNS:
        if re.search(pattern, text):
            return country
    return None


def normalize_source(value: object) -> str | None:
    """Remove field-fragment artifacts while preserving source identity."""
    if pd.isna(value):
        return None
    source = re.sub(r"\s+MONTH\s*=\s*[A-Z]+,?\s*$", "", str(value), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", source).strip(" ,")


def shorten(text: object, width: int = 48) -> str:
    value = re.sub(r"\s+", " ", str(text)).strip()
    return value if len(value) <= width else value[: width - 1].rstrip() + "…"
