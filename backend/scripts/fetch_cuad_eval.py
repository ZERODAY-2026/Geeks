"""Download 15 CUAD contracts and their labels for the grounding evaluation (set-up time, network allowed).

CUAD is public (Atticus Project, CC BY 4.0). The PDFs and labels go to backend/data/cuad/, which git ignores; they are
never committed. The 15 are chosen by a fixed seed over the sorted list of labelled contracts, so the choice is not
picked by hand.

Usage:  uv run --with huggingface_hub python scripts/fetch_cuad_eval.py
"""

from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download, list_repo_files

REPO = "theatticusproject/cuad"
PREFIX = "CUAD_v1/full_contract_pdf/"
N = 15
SEED = 0
OUT = Path(__file__).resolve().parents[1] / "data" / "cuad"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    labels_path = Path(hf_hub_download(REPO, "CUAD_v1/CUAD_v1.json", repo_type="dataset"))
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    titles = {article["title"] for article in labels["data"]}

    pdfs = {Path(f).stem.upper(): f for f in list_repo_files(REPO, repo_type="dataset") if f.startswith(PREFIX)}
    usable = sorted(t for t in titles if t.upper() in pdfs)
    chosen = random.Random(SEED).sample(usable, N)

    picked = []
    for title in chosen:
        remote = pdfs[title.upper()]
        local = Path(hf_hub_download(REPO, remote, repo_type="dataset"))
        target = OUT / Path(remote).name
        shutil.copy(local, target)
        picked.append({"title": title, "file": target.name})
    keep = {p["title"] for p in picked}
    subset = {"data": [a for a in labels["data"] if a["title"] in keep]}
    (OUT / "labels.json").write_text(json.dumps(subset, ensure_ascii=False), encoding="utf-8")
    (OUT / "contracts.json").write_text(json.dumps(picked, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(picked)} contracts (seed {SEED}) written to {OUT}; {len(usable)} labelled contracts had PDFs")


if __name__ == "__main__":
    main()
