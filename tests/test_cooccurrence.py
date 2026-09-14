from aggregate import cooccurrence as co


def test_pair_lift_math(six):
    pairs = co.pair_lift(six, min_freq=0.1, min_support=2, min_lift=1.0)
    d = {(p["a"], p["b"]): p for p in pairs}
    # aws & scoping co-occur in p1,p2,p3: P(ab)=0.5, P(a)=0.5, P(b)=0.5 -> lift 2.0
    assert d[("aws", "scoping")]["lift"] == 2.0 and d[("aws", "scoping")]["support"] == 3
    # python & aws: P(ab)=0.5, P(python)=1 -> lift 1.0 (kept because min_lift=1.0)
    assert d[("aws", "python")]["lift"] == 1.0


def test_pair_lift_filters(six):
    pairs = co.pair_lift(six, min_freq=0.1, min_support=2, min_lift=1.2)
    keys = {(p["a"], p["b"]) for p in pairs}
    assert ("aws", "scoping") in keys and ("aws", "python") not in keys


def test_cluster_stacks_groups_connected_pairs():
    pairs = [{"a": "aws", "b": "scoping", "lift": 2.0, "support": 3}, {"a": "aws", "b": "kubernetes", "lift": 1.5, "support": 2},
             {"a": "rag", "b": "evals", "lift": 3.0, "support": 4}]
    stacks = co.cluster_stacks(pairs, max_stacks=4, min_size=2)
    groups = [set(s["skills"]) for s in stacks]
    assert {"aws", "scoping", "kubernetes"} in groups and {"rag", "evals"} in groups
    assert stacks[0]["support"] >= stacks[-1]["support"]
