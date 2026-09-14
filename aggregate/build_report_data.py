"""Assemble every aggregate into the single JSON object the HTML template consumes."""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from aggregate import cooccurrence, criticality, frequency, gap, market
from extract import taxonomy
from extract.schema import Extraction
from sources.base import PROCESSED_DIR, Posting, normalize_company

META_MODEL = "claude-sonnet-5"
OUT = PROCESSED_DIR / "report_data.json"


def _outliers(skills: list[dict], mx: float, my: float) -> list[dict]:
    solid = [s for s in skills if not s["low_n"]]
    crit_q1 = statistics.quantiles([s["criticality"] for s in solid], n=4)[0] if len(solid) >= 4 else my
    hi_freq_lo_crit = sorted([s for s in solid if s["criticality"] <= crit_q1], key=lambda s: -s["frequency"])[:3]
    lo_freq_hi_crit = sorted([s for s in solid if s["frequency"] < mx and s["n"] >= 8], key=lambda s: -s["criticality"])[:3]
    out = [{"canonical": s["canonical"], "note": "Everyone asks; rarely the job itself"} for s in hi_freq_lo_crit]
    out += [{"canonical": s["canonical"], "note": "Rarely listed; when it is, it's the job"} for s in lo_freq_hi_crit]
    return out


def _stack_name(skills: list[str], tx: taxonomy.Taxonomy) -> str:
    return " + ".join(tx.labels.get(s, s) for s in skills[:3])


def build(exs: list[Extraction], postings: list[Posting], stats: list[dict], n_rejects: int,
          tx: taxonomy.Taxonomy, *, generated_at: str) -> dict:
    freq = frequency.skill_frequency(exs)
    crit = criticality.skill_criticality(exs)
    skills = []
    for c, f in freq.items():
        skills.append({"canonical": c, "label": tx.labels[c], "cluster": tx.cluster_of(c), "n": f["n"],
                       "frequency": round(f["frequency"], 4), "criticality": round(crit[c]["criticality"], 4),
                       "mentions": crit[c]["mentions"], "low_n": crit[c]["low_n"], "evidence": crit[c]["evidence"]})
    skills.sort(key=lambda s: -s["frequency"])
    cov = frequency.cluster_coverage(exs, tx)
    clusters = [{"key": k, "label": tx.cluster_labels[k], "coverage": round(cov[k], 4),
                 "skills": [s.canonical for s in v if s.canonical in freq]} for k, v in tx.clusters.items()]
    fx = [s["frequency"] for s in skills] or [0]
    fy = [s["criticality"] for s in skills if not s["low_n"]] or [0]
    mx, my = statistics.median(fx), statistics.median(fy)
    pairs = cooccurrence.pair_lift(exs)
    stacks = [{"name": _stack_name(s["skills"], tx), "skills": s["skills"], "support": s["support"]}
              for s in cooccurrence.cluster_stacks(pairs)]
    mkt = market.distributions(exs)
    mkt["segment_deltas"] = market.segment_deltas(exs, postings)
    dates = sorted(p.posted_date for p in postings if p.posted_date)
    return {
        "meta": {"n_postings": len(exs), "n_companies": len({normalize_company(p.company) for p in postings}),
                 "date_range": [dates[0], dates[-1]] if dates else ["", ""], "generated_at": generated_at, "model": META_MODEL,
                 "sources": stats, "segmentation": {"header": sum(e.segmentation_quality == "header" for e in exs),
                                                     "inferred": sum(e.segmentation_quality == "inferred" for e in exs)},
                 "rejects": n_rejects, "adzuna_used": False},
        "skills": skills,
        "clusters": clusters,
        "scatter": {"median_frequency": round(mx, 4), "median_criticality": round(my, 4), "outliers": _outliers(skills, mx, my)},
        "stacks": stacks,
        "market": mkt,
        "gap": [{"canonical": g["canonical"], "label": tx.labels[g["canonical"]], "frequency": g["frequency"]} for g in gap.gaps(freq)],
    }


def run() -> Path:
    from extract.validate import load_valid_extractions
    from sources.collect import load_postings
    exs = load_valid_extractions()
    done = {e.posting_id for e in exs}
    postings = [p for p in load_postings() if p.id in done]
    stats = json.loads((PROCESSED_DIR / "collect_stats.json").read_text())
    rejects_path = PROCESSED_DIR / "rejects.log"
    n_rejects = len(rejects_path.read_text().splitlines()) if rejects_path.exists() else 0
    data = build(exs, postings, stats, n_rejects, taxonomy.load(), generated_at=datetime.now(timezone.utc).isoformat())
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"report_data.json: n={data['meta']['n_postings']} skills={len(data['skills'])} stacks={len(data['stacks'])} gaps={len(data['gap'])}")
    for s in data["stacks"]:
        print(f"  stack support={s['support']:3d}  {s['name']}  <- {s['skills']}")
    return OUT
