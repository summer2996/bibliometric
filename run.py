from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parent
SCRIPTS = [
    "figures/figure1a.py",
    "figures/figure1b.py",
    "figures/figure2a.py",
    "figures/figure2b.py",
    "figures/figure3a.py",
    "figures/figure3b.py",
    "figures/figure4_bibliometric_laws.py",
    "figures/figure5_network_centrality.py",
    "tables.py",
]


for script in SCRIPTS:
    print(f"Running {script} ...")
    runpy.run_path(ROOT / script, run_name="__main__")

print("All figures and tables were generated successfully.")
