"""Assemble every aggregate into the single JSON object the HTML template consumes."""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aggregate import cooccurrence, criticality, frequency, gap, market
from extract import taxonomy
from extract.schema import Extraction
from sources.base import PROCESSED_DIR, Posting, normalize_company

META_MODEL = "claude-sonnet-5"
OUT = PROCESSED_DIR / "report_data.json"
OPEN_VOCAB_PATH = PROCESSED_DIR / "open_vocab_sample.json"

STACK_NAME_OVERRIDES: dict[frozenset, str] = {
    # Re-checked 2026-09-15 after the 12-month window + taxonomy move (cloud_platforms ->
    # deployment_and_operations) changed which skills co-occur; stack membership shifted, so the
    # frozenset keys below were updated to match. Three of the four names were kept because the new
    # membership is still a reasonable fit; the fourth ("ML operations & delivery") no longer
    # described its stack (which is now RAG/evals/guardrails/prompt-engineering, not
    # cost/model-serving ops) and was renamed to "LLM application core".
    frozenset({"expectation_management", "rest_apis", "learning_agility", "consulting", "training_enablement", "pre_sales", "enterprise_systems"}): "Pre-sales & field delivery",
    frozenset({"python", "security_compliance", "typescript", "sql", "product_sense", "react"}): "Full-stack builder",
    frozenset({"evals", "rag", "guardrails_safety", "prompt_engineering", "auth_identity", "git", "llm_frameworks"}): "LLM application core",
    frozenset({"aws", "gcp", "azure", "kubernetes", "ci_cd", "docker", "iac"}): "Cloud infrastructure",
}

_DEFAULT_CRIT = {"criticality": 0.0, "mentions": {s: 0 for s in criticality.SECTIONS}, "low_n": True, "evidence": ""}


def within_window(postings: list[Posting], collected_on, days: int = 365) -> list[Posting]:
    """Keep postings whose posted_date falls on or after `collected_on - days`. `collected_on`
    is a date; every posting is expected to carry a posted_date, but one without is dropped
    defensively rather than crashing."""
    cutoff = collected_on - timedelta(days=days)
    out = []
    for p in postings:
        if not p.posted_date:
            continue
        try:
            pd = datetime.strptime(p.posted_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        if pd >= cutoff:
            out.append(p)
    return out


def _outliers(skills: list[dict], mx: float, my: float) -> list[dict]:
    solid = [s for s in skills if not s["low_n"] and s["n"] >= 20]
    crit_q1 = statistics.quantiles([s["criticality"] for s in solid], n=4)[0] if len(solid) >= 4 else my
    hi_freq_lo_crit = sorted([s for s in solid if s["criticality"] <= crit_q1], key=lambda s: -s["frequency"])[:3]
    lo_freq_hi_crit = sorted([s for s in solid if s["frequency"] < mx], key=lambda s: -s["criticality"])[:3]
    out = [{"canonical": s["canonical"], "note": "Everyone asks; rarely the job itself"} for s in hi_freq_lo_crit]
    out += [{"canonical": s["canonical"], "note": "Rarely listed; when it is, it's the job"} for s in lo_freq_hi_crit]
    return out


def _stack_name(skills: list[str], tx: taxonomy.Taxonomy) -> str:
    override = STACK_NAME_OVERRIDES.get(frozenset(skills))
    if override:
        return override
    return " + ".join(tx.labels.get(s, s) for s in skills[:3])


def _criticality_basis(skills: list[dict], header_crit: dict, all_crit: dict, mx: float, my: float, *,
                        n_header_postings: int, n_postings: int) -> dict:
    """Robustness check: how different is criticality-on-header-only vs criticality-on-all-postings?"""
    candidates = [s["canonical"] for s in skills if not s["low_n"]]
    freq_by_c = {s["canonical"]: s["frequency"] for s in skills}
    if len(candidates) < 2:
        return {"postings": n_header_postings, "of": n_postings, "spearman_vs_all": 0.0, "quadrant_flips": 0, "skills": len(candidates)}
    xs = [header_crit.get(c, _DEFAULT_CRIT)["criticality"] for c in candidates]
    ys = [all_crit.get(c, _DEFAULT_CRIT)["criticality"] for c in candidates]
    rho = round(criticality.spearman(xs, ys), 3)
    my_all = statistics.median(ys)
    flips = 0
    for c, y in zip(candidates, ys):
        q_header = (freq_by_c[c] >= mx, header_crit.get(c, _DEFAULT_CRIT)["criticality"] >= my)
        q_all = (freq_by_c[c] >= mx, y >= my_all)
        if q_header != q_all:
            flips += 1
    return {"postings": n_header_postings, "of": n_postings, "spearman_vs_all": rho, "quadrant_flips": flips, "skills": len(candidates)}


def build(exs: list[Extraction], postings: list[Posting], stats: list[dict], n_rejects: int,
          tx: taxonomy.Taxonomy, *, generated_at: str, collect_meta: dict | None = None) -> dict:
    freq = frequency.skill_frequency(exs)
    header_exs = [e for e in exs if e.segmentation_quality == "header"]
    header_crit = criticality.skill_criticality(header_exs)
    all_crit = criticality.skill_criticality(exs)
    skills = []
    for c, f in freq.items():
        cc = header_crit.get(c, _DEFAULT_CRIT)
        crit_n = sum(cc["mentions"].values())
        skills.append({"canonical": c, "label": tx.labels[c], "cluster": tx.cluster_of(c), "n": f["n"],
                       "frequency": round(f["frequency"], 4), "criticality": round(cc["criticality"], 4),
                       "mentions": cc["mentions"], "crit_n": crit_n, "low_n": cc["low_n"], "evidence": cc["evidence"]})
    skills.sort(key=lambda s: (-s["frequency"], s["canonical"]))
    cov = frequency.cluster_coverage(exs, tx)
    clusters = [{"key": k, "label": tx.cluster_labels[k], "coverage": round(cov[k], 4),
                 "skills": [s.canonical for s in v if s.canonical in freq]} for k, v in tx.clusters.items()]
    fx = [s["frequency"] for s in skills] or [0]
    fy = [s["criticality"] for s in skills if not s["low_n"]] or [0]
    mx, my = statistics.median(fx), statistics.median(fy)
    crit_basis = _criticality_basis(skills, header_crit, all_crit, mx, my,
                                     n_header_postings=len(header_exs), n_postings=len(exs))
    pairs = cooccurrence.pair_lift(exs)
    sets = [frozenset(s.canonical for s in e.skills) for e in exs]
    stacks = [{"name": _stack_name(s["skills"], tx), "skills": s["skills"], "support": s["support"]}
              for s in cooccurrence.cluster_stacks(pairs, postings=sets)]
    mkt = market.distributions(exs)
    mkt["segment_n"] = market.segment_n(postings)
    mkt["segment_deltas"] = market.segment_deltas(exs, postings)
    dates = sorted(p.posted_date for p in postings if p.posted_date)
    collected_on = collect_meta["collected_at"][:10] if collect_meta else generated_at[:10]
    cluster_of = {c: tx.cluster_of(c) for c in freq}
    return {
        "meta": {"n_postings": len(exs), "n_companies": len({normalize_company(p.company) for p in postings}),
                 "date_range": [dates[0], dates[-1]] if dates else ["", ""], "generated_at": generated_at, "model": META_MODEL,
                 "collected_on": collected_on, "criticality_basis": crit_basis, "open_vocab": None,
                 "hn_threads": collect_meta.get("hn_threads") if collect_meta else None,
                 "sources": stats, "segmentation": {"header": sum(e.segmentation_quality == "header" for e in exs),
                                                     "inferred": sum(e.segmentation_quality == "inferred" for e in exs)},
                 "rejects": n_rejects, "adzuna_used": False},
        "skills": skills,
        "clusters": clusters,
        "scatter": {"median_frequency": round(mx, 4), "median_criticality": round(my, 4), "outliers": _outliers(skills, mx, my)},
        "stacks": stacks,
        "market": mkt,
        "gap": [{"canonical": g["canonical"], "label": tx.labels[g["canonical"]], "frequency": g["frequency"]} for g in gap.gaps(freq, cluster_of)],
    }


def run() -> Path:
    from extract.validate import load_valid_extractions
    from sources.collect import load_postings
    all_postings = load_postings()
    posting_ids = {p.id for p in all_postings}
    # symmetric filter: an extraction only counts if its posting is still current, and a posting
    # only counts if it has a current extraction (a posting dropped by a later re-collect must not
    # leave its stale extraction inflating n_postings; an extraction that outlived its posting must
    # not either).
    exs = [e for e in load_valid_extractions() if e.posting_id in posting_ids]
    done = {e.posting_id for e in exs}
    postings = [p for p in all_postings if p.id in done]
    stats = json.loads((PROCESSED_DIR / "collect_stats.json").read_text())
    rejects_path = PROCESSED_DIR / "rejects.log"
    n_rejects = len(rejects_path.read_text().splitlines()) if rejects_path.exists() else 0
    meta_path = PROCESSED_DIR / "collect_meta.json"
    collect_meta = json.loads(meta_path.read_text()) if meta_path.exists() else None
    generated_at = datetime.now(timezone.utc).isoformat()
    collected_on_str = collect_meta["collected_at"][:10] if collect_meta else generated_at[:10]
    collected_on = datetime.strptime(collected_on_str, "%Y-%m-%d").date()

    # 12-month window: only keep postings first published within the last 365 days of collection.
    collected_count = len(postings)
    windowed_postings = within_window(postings, collected_on)
    windowed_ids = {p.id for p in windowed_postings}
    windowed_exs = [e for e in exs if e.posting_id in windowed_ids]
    excluded_older = collected_count - len(windowed_postings)

    data = build(windowed_exs, windowed_postings, stats, n_rejects, taxonomy.load(), generated_at=generated_at,
                 collect_meta=collect_meta)
    cutoff = collected_on - timedelta(days=365)
    data["meta"]["window"] = {"from": cutoff.isoformat(), "to": collected_on.isoformat(),
                               "collected": collected_count, "excluded_older": excluded_older}

    # open-vocabulary coverage hook: only present once the sampling pass has been run.
    if OPEN_VOCAB_PATH.exists():
        data["meta"]["open_vocab"] = json.loads(OPEN_VOCAB_PATH.read_text())["summary"]

    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"report_data.json: n={data['meta']['n_postings']} skills={len(data['skills'])} stacks={len(data['stacks'])} gaps={len(data['gap'])}")
    print(f"  window: {data['meta']['window']}")
    print(f"  criticality_basis: {data['meta']['criticality_basis']}")
    for s in data["stacks"]:
        print(f"  stack support={s['support']:3d}  {s['name']}  <- {s['skills']}")
    return OUT
