"""Seniority / years / travel / customer-facing distributions, verbs, startup-vs-enterprise deltas."""
from __future__ import annotations

from collections import Counter

from extract.schema import Extraction
from sources.base import Posting

SENIORITY = ["junior", "mid", "senior", "staff_plus", "unspecified"]
YEARS = ["0-2", "3-5", "6-9", "10+", "unspecified"]
TRAVEL = ["none", "occasional", "frequent", "unspecified"]


def _years_bucket(y: int | None) -> str:
    if y is None:
        return "unspecified"
    return "0-2" if y <= 2 else "3-5" if y <= 5 else "6-9" if y <= 9 else "10+"


def distributions(exs: list[Extraction]) -> dict:
    sen = Counter(e.seniority for e in exs)
    yrs = Counter(_years_bucket(e.years_required) for e in exs)
    trv = Counter(e.travel_expectation for e in exs)
    cfi = Counter(str(e.customer_facing_intensity) for e in exs)
    verbs = Counter(v.lower().strip() for e in exs for v in e.responsibility_verbs)
    return {
        "seniority": {k: sen.get(k, 0) for k in SENIORITY},
        "years": {k: yrs.get(k, 0) for k in YEARS},
        "travel": {k: trv.get(k, 0) for k in TRAVEL},
        "customer_facing": {k: cfi.get(k, 0) for k in "12345"},
        "verbs": [[v, n] for v, n in verbs.most_common(15)],
    }


STARTUP_HINTS = {"startup", "scaleup"}
ENTERPRISE_HINTS = {"enterprise"}


def _segment_ids(postings: list[Posting]) -> dict[str, set[str]]:
    """Posting ids per segment, excluding HN postings (short/unstructured; skew the comparison)."""
    non_hn = [p for p in postings if p.source != "hn"]
    return {"startup": {p.id for p in non_hn if p.company_size_hint in STARTUP_HINTS},
            "enterprise": {p.id for p in non_hn if p.company_size_hint in ENTERPRISE_HINTS}}


def segment_n(postings: list[Posting]) -> dict:
    ids = _segment_ids(postings)
    return {"startup": len(ids["startup"]), "enterprise": len(ids["enterprise"])}


def _segment_freq(exs: list[Extraction], postings: list[Posting]) -> tuple[dict[str, float], dict[str, float]]:
    """Share of postings mentioning each skill, per segment. Empty dicts if either segment is empty."""
    ids = _segment_ids(postings)
    groups = {"startup": [e for e in exs if e.posting_id in ids["startup"]],
              "enterprise": [e for e in exs if e.posting_id in ids["enterprise"]]}
    if not groups["startup"] or not groups["enterprise"]:
        return {}, {}
    def freq(group):
        c = Counter(s for e in group for s in {m.canonical for m in e.skills})
        return {k: v / len(group) for k, v in c.items()}
    return freq(groups["startup"]), freq(groups["enterprise"])


def segment_freq(exs: list[Extraction], postings: list[Posting]) -> list[dict]:
    """Every skill with its startup and enterprise share, no threshold — so a consumer can show
    a cluster in full (e.g. the AI skills, which mostly do NOT differ between segments and so
    never appear in segment_deltas). Sorted by combined share, highest first."""
    fs, fe = _segment_freq(exs, postings)
    out = [{"skill": skill, "startup": round(fs.get(skill, 0.0), 3), "enterprise": round(fe.get(skill, 0.0), 3)}
           for skill in set(fs) | set(fe)]
    return sorted(out, key=lambda d: (-(d["startup"] + d["enterprise"]), d["skill"]))


def segment_deltas(exs: list[Extraction], postings: list[Posting], freq_threshold: float = 0.15) -> list[dict]:
    """Skills whose startup and enterprise shares differ by at least `freq_threshold`, widest gap first."""
    fs, fe = _segment_freq(exs, postings)
    out = []
    for skill in set(fs) | set(fe):
        a, b = fs.get(skill, 0.0), fe.get(skill, 0.0)
        if abs(a - b) >= freq_threshold:
            out.append({"skill": skill, "startup": round(a, 3), "enterprise": round(b, 3)})
    return sorted(out, key=lambda d: -abs(d["startup"] - d["enterprise"]))
