"""Grounding evaluation on 15 CUAD contracts (local only; the contracts are never committed).

For each contract, the analysis runs on the five MSA topics that map to a CUAD category. CUAD's labels say whether a
category is present (it has an annotated answer) or absent. Each topic's answer is scored against that label:

  over-claim        absent in CUAD, but the model says ENTAILED or CONTRADICTED  (the grounding failure)
  false silence     present in CUAD, but the model says NOT_MENTIONED
  detection         present in CUAD, and the model says ENTAILED or CONTRADICTED
  grounded          a detection whose cited quote overlaps the labelled answer text

Run once with the gate on and once off, for the comparison:
  uv run python scripts/eval_cuad.py --label gate_on
  LEXISHIELD_VERIFY__RELEVANCE_GATE=false uv run python scripts/eval_cuad.py --label gate_off

Usage needs scripts/fetch_cuad_eval.py to have run first. Results go to eval/results/cuad_<label>.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys

from lexishield.agents import orchestrator
from lexishield.agents.orchestrator import run_analysis
from lexishield.ingest.pipeline import ingest_pdf
from lexishield.llm.gateway import LLMGateway
from lexishield.models import AnalyzeRequest, ChecklistStatus, DocType
from lexishield.packs import all_packs
from lexishield.settings import BACKEND_DIR, Settings
from lexishield.verify.quotes import normalize

DATA = BACKEND_DIR / "data" / "cuad"
CATEGORY_TO_TOPIC = {
    "Governing Law": "msa.governing_law",
    # Not mapped: msa.termination_kill_fee asks how either side can end the contract, which almost every contract
    # states, while CUAD's 'Termination For Convenience' labels only termination without cause.
    "No-Solicit Of Employees": "msa.non_solicit",
    "No-Solicit Of Customers": "msa.non_solicit",
    "IP Ownership Assignment": "msa.ip_transfer",
    "Cap On Liability": "msa.liability_cap",
    "Uncapped Liability": "msa.liability_cap",
    "Anti-Assignment": "msa.assignment",
}
CLAIMS = {ChecklistStatus.ENTAILED, ChecklistStatus.CONTRADICTED}
CATEGORY_RE = re.compile(r'related to "([^"]+)"')
MIN_OVERLAP = 30


def category_of(question: str) -> str | None:
    m = CATEGORY_RE.search(question)
    return m.group(1) if m else None


def labels_by_title() -> dict[str, dict[str, list[str]]]:
    """title -> category -> annotated answer texts (empty list = the category is absent)."""
    data = json.loads((DATA / "labels.json").read_text(encoding="utf-8"))["data"]
    out: dict[str, dict[str, list[str]]] = {}
    for article in data:
        cats: dict[str, list[str]] = {}
        for para in article["paragraphs"]:
            for qa in para["qas"]:
                cat = category_of(qa["question"])
                if cat is None:
                    continue
                texts = (
                    [] if qa.get("is_impossible") else [a["text"] for a in qa.get("answers", []) if a["text"].strip()]
                )
                cats.setdefault(cat, []).extend(texts)
        out[article["title"]] = cats
    return out


def overlaps(quote: str, answers: list[str]) -> bool:
    q = normalize(quote).text.strip()
    for answer in answers:
        a = normalize(answer).text.strip()
        short, long_ = sorted((q, a), key=len)
        if len(short) >= MIN_OVERLAP and short in long_:
            return True
    return False


def restricted_pack(settings: Settings):  # type: ignore[no-untyped-def]
    """Evaluation only: the msa pack with just the mapped topics, so each contract takes minutes, not hours."""
    pack = all_packs(settings)["msa_generic"]
    keep = set(CATEGORY_TO_TOPIC.values())
    return pack.model_copy(update={"topics": [t for t in pack.topics if t.id in keep]})


async def evaluate(label: str) -> dict:
    settings = Settings()
    gw = LLMGateway(settings)
    contracts = json.loads((DATA / "contracts.json").read_text(encoding="utf-8"))
    labels = labels_by_title()
    pack = restricted_pack(settings)
    orchestrator.pack_for = lambda doc_type, s=None: pack  # evaluation only: the mapped topics for every contract

    async def emit(name: str, data: dict) -> None:
        return None

    rows = []
    for entry in contracts:
        title = entry["title"]
        cats = labels.get(title, {})
        present: dict[str, bool] = {}
        answers: dict[str, list[str]] = {}
        for cat, topic in CATEGORY_TO_TOPIC.items():
            texts = cats.get(cat, [])
            answers.setdefault(topic, []).extend(texts)
            present[topic] = present.get(topic, False) or bool(texts)
        row = {"title": title, "file": entry["file"], "items": [], "error": None}
        try:
            ing = ingest_pdf((DATA / entry["file"]).read_bytes(), entry["file"])
            report = await run_analysis(
                gw, settings, ing, "doc_eval", AnalyzeRequest(doc_type=DocType.MSA), emit, lambda: False
            )
        except Exception as e:  # one unreadable contract must not stop the evaluation
            row["error"] = type(e).__name__
            rows.append(row)
            print(f"  {title[:50]}: error {type(e).__name__}", flush=True)
            continue
        cards = {c.topic_id: c for c in report.cards}
        for item in report.checklist:
            topic = item.topic_id
            claim = item.status in CLAIMS
            grounded = claim and any(overlaps(c.quote, answers.get(topic, [])) for c in item.evidence)
            row["items"].append(
                {
                    "topic": topic,
                    "present": present.get(topic, False),
                    "status": item.status.value,
                    "evidence": len(item.evidence),
                    "grounded": grounded,
                    "card": cards[topic].tier.value if topic in cards else None,
                }
            )
        rows.append(row)
        print(f"  {title[:50]}: {len(row['items'])} topics", flush=True)

    scored = [i for r in rows for i in r["items"]]
    absent = [i for i in scored if not i["present"]]
    present_items = [i for i in scored if i["present"]]
    summary = {
        "label": label,
        "gate": settings.verify.relevance_gate,
        "contracts": len(contracts),
        "errors": sum(1 for r in rows if r["error"]),
        "topic_checks": len(scored),
        "absent_checks": len(absent),
        "present_checks": len(present_items),
        "over_claims": sum(i["status"] in {s.value for s in CLAIMS} for i in absent),
        "false_silences": sum(i["status"] == ChecklistStatus.NOT_MENTIONED.value for i in present_items),
        "detections": sum(i["status"] in {s.value for s in CLAIMS} for i in present_items),
        "grounded_detections": sum(i["grounded"] for i in present_items),
    }
    return {"summary": summary, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    args = ap.parse_args()
    result = asyncio.run(evaluate(args.label))
    out = BACKEND_DIR / "eval" / "results" / f"cuad_{args.label}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    s = result["summary"]
    print(json.dumps(s, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
