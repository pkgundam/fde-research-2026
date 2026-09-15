from aggregate import market, gap
from extract.schema import Extraction, SkillMention as M
from sources.base import Posting


def test_distributions(six):
    d = market.distributions(six)
    assert d["seniority"] == {"junior": 1, "mid": 1, "senior": 2, "staff_plus": 1, "unspecified": 1}
    assert d["years"] == {"0-2": 1, "3-5": 2, "6-9": 1, "10+": 1, "unspecified": 1}
    assert d["travel"] == {"none": 1, "occasional": 2, "frequent": 1, "unspecified": 2}
    assert d["customer_facing"] == {"1": 1, "2": 1, "3": 1, "4": 2, "5": 1}
    assert d["verbs"][0] == ["deploy", 6] and len(d["verbs"]) <= 15


def _mk(pid, skills, size_hint, source="greenhouse"):
    ex = Extraction(posting_id=pid, skills=[M(canonical=c, section=s, evidence=f"{c} {s}") for c, s in skills],
                     seniority="mid", years_required=3, travel_expectation="occasional", customer_facing_intensity=3,
                     responsibility_verbs=["build", "deploy", "scope", "own", "present"], segmentation_quality="header")
    post = Posting(id=pid, title="t", company="c", url="u", full_text="x", source=source, company_size_hint=size_hint)
    return ex, post


def test_segment_deltas():
    # startup group (after exclusions): p1, p2 (startup) + p3 (scaleup, counted as startup) -> n=3
    # scoping present in all three -> startup freq 1.0; absent from enterprise -> enterprise freq 0.0
    # python present in every posting in both groups -> freq 1.0 vs 1.0 -> no delta
    e1, po1 = _mk("p1", [("scoping", "responsibility"), ("python", "requirement")], "startup")
    e2, po2 = _mk("p2", [("scoping", "responsibility"), ("python", "requirement")], "startup")
    e3, po3 = _mk("p3", [("scoping", "responsibility"), ("python", "requirement")], "scaleup")
    e4, po4 = _mk("e1", [("python", "requirement")], "enterprise")
    e5, po5 = _mk("e2", [("python", "requirement")], "enterprise")
    # HN posting mentions only kubernetes; if wrongly included in the startup group (n=4) this would give
    # kubernetes a startup freq of 0.25 (>= the 0.2 threshold below) vs 0.0 enterprise -> a spurious delta.
    # Correctly excluded, the startup group stays n=3 with kubernetes freq 0.0 -> no delta.
    e6, po6 = _mk("hn1", [("kubernetes", "responsibility")], "startup", source="hn")

    exs = [e1, e2, e3, e4, e5, e6]
    posts = [po1, po2, po3, po4, po5, po6]

    deltas = market.segment_deltas(exs, posts, freq_threshold=0.2)
    d = {x["skill"]: x for x in deltas}
    assert d["scoping"] == {"skill": "scoping", "startup": 1.0, "enterprise": 0.0}
    assert "python" not in d  # 1.0 vs 1.0, no delta
    assert "kubernetes" not in d  # proves the hn posting is excluded from both groups

    assert market.segment_n(posts) == {"startup": 3, "enterprise": 2}

    # segment_freq keeps every skill, including the ones with no delta, and still excludes hn
    f = {x["skill"]: x for x in market.segment_freq(exs, posts)}
    assert f["python"] == {"skill": "python", "startup": 1.0, "enterprise": 1.0}
    assert f["scoping"] == {"skill": "scoping", "startup": 1.0, "enterprise": 0.0}
    assert "kubernetes" not in f
    assert [x["skill"] for x in market.segment_freq(exs, posts)][0] == "python"  # highest combined share first


def test_gap():
    freq = {"python": {"frequency": 0.9}, "scoping": {"frequency": 0.4}, "rag": {"frequency": 0.5},
            "travel_onsite": {"frequency": 0.1}, "written_communication": {"frequency": 0.8},
            "domain_expertise": {"frequency": 0.35}}
    cluster_of = {"python": "software_foundations", "scoping": "customer_delivery", "rag": "ai_application_engineering",
                  "travel_onsite": "customer_delivery", "written_communication": "product_thinking_and_communication",
                  "domain_expertise": "customer_delivery"}
    g = gap.gaps(freq, cluster_of, min_frequency=0.2)
    # python/rag are technical-cluster skills (roadmaps teach them); written_communication is generic
    # professional (every job asks); travel_onsite is below the frequency threshold.
    assert [x["canonical"] for x in g] == ["scoping", "domain_expertise"]
    assert "software_foundations" in gap.TECHNICAL_CLUSTERS and "written_communication" in gap.GENERIC_PROFESSIONAL


def test_gap_capped_at_limit():
    freq = {f"skill_{i}": {"frequency": 0.9 - i * 0.01} for i in range(12)}
    cluster_of = {k: "customer_delivery" for k in freq}
    g = gap.gaps(freq, cluster_of, min_frequency=0.3, limit=8)
    assert len(g) == 8
    assert [x["canonical"] for x in g] == [f"skill_{i}" for i in range(8)]
