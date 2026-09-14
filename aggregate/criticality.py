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
