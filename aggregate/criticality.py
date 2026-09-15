"""Share of a skill's mentions that are responsibilities (vs requirement / nice-to-have)."""
from __future__ import annotations

from collections import defaultdict

from extract.schema import Extraction

SECTIONS = ("responsibility", "requirement", "nice_to_have")


def skill_criticality(exs: list[Extraction], low_n: int = 5) -> dict[str, dict]:
    mentions: dict[str, dict[str, int]] = defaultdict(lambda: {s: 0 for s in SECTIONS})
    evidence: dict[str, str] = {}
    for e in exs:
        for s in e.skills:
            mentions[s.canonical][s.section] += 1
            if s.section == "responsibility" or s.canonical not in evidence:
                evidence[s.canonical] = s.evidence  # prefer a responsibility quote
    out = {}
    for c, m in mentions.items():
        total = sum(m.values())
        out[c] = {"criticality": m["responsibility"] / total if total else 0.0, "mentions": dict(m),
                  "low_n": total < low_n, "evidence": evidence.get(c, "")}
    return out


def _rank(values: list[float]) -> list[float]:
    """1-based ranks, ties given the average rank of the tied positions."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman rank correlation (Pearson correlation of ranks, with average ranks for ties)."""
    n = len(xs)
    if n < 2 or len(ys) != n:
        return 0.0
    rx, ry = _rank(xs), _rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    varx = sum((a - mx) ** 2 for a in rx)
    vary = sum((b - my) ** 2 for b in ry)
    if varx == 0 or vary == 0:
        return 0.0
    return cov / (varx * vary) ** 0.5
