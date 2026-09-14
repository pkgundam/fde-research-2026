"""Skill-pair lift and greedy grouping into 'stacks that travel together'."""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations

from extract.schema import Extraction


def pair_lift(exs: list[Extraction], *, min_freq: float = 0.05, min_support: int = 8, min_lift: float = 1.2) -> list[dict]:
    n = len(exs)
    sets = [frozenset(s.canonical for s in e.skills) for e in exs]
    single = Counter(c for s in sets for c in s)
    eligible = {c for c, k in single.items() if k / n >= min_freq}
    pair = Counter()
    for s in sets:
        for a, b in combinations(sorted(s & eligible), 2):
            pair[(a, b)] += 1
    out = []
    for (a, b), k in pair.items():
        lift = (k / n) / ((single[a] / n) * (single[b] / n))
        if k >= min_support and lift >= min_lift:
            out.append({"a": a, "b": b, "lift": round(lift, 3), "support": k})
    return sorted(out, key=lambda p: (-p["lift"], -p["support"]))


def cluster_stacks(pairs: list[dict], *, max_stacks: int = 4, min_size: int = 2) -> list[dict]:
    """Greedy: take strongest edges first, merge into groups; split large groups by dropping weakest cross edges."""
    adj: dict[str, dict[str, float]] = defaultdict(dict)
    for p in pairs:
        adj[p["a"]][p["b"]] = adj[p["b"]][p["a"]] = p["lift"]
    group_of: dict[str, int] = {}
    groups: dict[int, set[str]] = {}
    nxt = 0
    for p in sorted(pairs, key=lambda p: -p["lift"]):
        ga, gb = group_of.get(p["a"]), group_of.get(p["b"])
        if ga is None and gb is None:
            groups[nxt] = {p["a"], p["b"]}; group_of[p["a"]] = group_of[p["b"]] = nxt; nxt += 1
        elif ga is None:
            groups[gb].add(p["a"]); group_of[p["a"]] = gb
        elif gb is None:
            groups[ga].add(p["b"]); group_of[p["b"]] = ga
        elif ga != gb and len(groups[ga]) + len(groups[gb]) <= 8:
            groups[ga] |= groups[gb]
            for s in groups[gb]:
                group_of[s] = ga
            del groups[gb]
    support = {(p["a"], p["b"]): p["support"] for p in pairs}
    out = []
    for g in groups.values():
        if len(g) < min_size:
            continue
        sup = max((support.get((a, b), support.get((b, a), 0)) for a, b in combinations(sorted(g), 2)), default=0)
        out.append({"skills": sorted(g, key=lambda s: -sum(adj[s].get(o, 0) for o in g)), "support": sup})
    return sorted(out, key=lambda s: -s["support"])[:max_stacks]
