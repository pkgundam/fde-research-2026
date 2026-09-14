"""How often each skill / cluster appears across postings."""
from __future__ import annotations

from collections import Counter

from extract.schema import Extraction
from extract.taxonomy import Taxonomy


def skill_frequency(exs: list[Extraction]) -> dict[str, dict]:
    n = len(exs)
    counts = Counter(c for e in exs for c in {s.canonical for s in e.skills})
    return {c: {"n": k, "frequency": k / n if n else 0.0} for c, k in counts.items()}


def cluster_coverage(exs: list[Extraction], tx: Taxonomy) -> dict[str, float]:
    n = len(exs)
    out = {}
    for key, skills in tx.clusters.items():
        members = {s.canonical for s in skills}
        hit = sum(1 for e in exs if any(s.canonical in members for s in e.skills))
        out[key] = hit / n if n else 0.0
    return out
