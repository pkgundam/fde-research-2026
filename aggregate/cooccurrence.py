"""Skill-pair lift and greedy grouping into 'stacks that travel together'."""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations

from extract.schema import Extraction


def pair_lift(exs: list[Extraction], *, min_freq: float = 0.08, max_freq: float = 0.6, min_lift: float = 1.5,
              min_support: int = 10) -> list[dict]:
    n = len(exs)
    sets = [frozenset(s.canonical for s in e.skills) for e in exs]
    single = Counter(c for s in sets for c in s)
    eligible = {c for c, k in single.items() if min_freq <= k / n <= max_freq}
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


def cluster_stacks(pairs: list[dict], *, max_stacks: int = 4, min_size: int = 3, cap: int = 7,
                    postings: list[frozenset] | None = None) -> list[dict]:
    """Greedy: take strongest edges first, enforcing `cap` on every single-node or group-merge addition."""
    adj: dict[str, dict[str, float]] = defaultdict(dict)
    for p in pairs:
        adj[p["a"]][p["b"]] = adj[p["b"]][p["a"]] = p["lift"]
    group_of: dict[str, int] = {}
    groups: dict[int, set[str]] = {}
    nxt = 0
    for p in sorted(pairs, key=lambda p: (-p["lift"], -p["support"], p["a"], p["b"])):
        a, b = p["a"], p["b"]
        ga, gb = group_of.get(a), group_of.get(b)
        if ga is None and gb is None:
            if cap < 2:
                continue
            groups[nxt] = {a, b}
            group_of[a] = group_of[b] = nxt
            nxt += 1
        elif ga is None:
            if len(groups[gb]) < cap:
                groups[gb].add(a)
                group_of[a] = gb
        elif gb is None:
            if len(groups[ga]) < cap:
                groups[ga].add(b)
                group_of[b] = ga
        elif ga != gb and len(groups[ga]) + len(groups[gb]) <= cap:
            groups[ga] |= groups[gb]
            for s in groups[gb]:
                group_of[s] = ga
            del groups[gb]

    support_pair = {(p["a"], p["b"]): p["support"] for p in pairs}
    skill_freq: Counter = Counter()
    if postings is not None:
        for s in postings:
            for skill in s:
                skill_freq[skill] += 1

    out = []
    for g in groups.values():
        if len(g) < min_size:
            continue
        if postings is not None:
            need = min(3, len(g))
            sup = sum(1 for s in postings if len(g & s) >= need)
            ordered = sorted(g, key=lambda s: (-skill_freq[s], s))
        else:
            sup = max((support_pair.get((a, b), support_pair.get((b, a), 0)) for a, b in combinations(sorted(g), 2)), default=0)
            ordered = sorted(g, key=lambda s: (-sum(adj[s].get(o, 0) for o in g), s))
        out.append({"skills": ordered, "support": sup})
    return sorted(out, key=lambda s: -s["support"])[:max_stacks]
