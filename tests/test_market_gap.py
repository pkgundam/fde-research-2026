from aggregate import market, gap
from sources.base import Posting


def test_distributions(six):
    d = market.distributions(six)
    assert d["seniority"] == {"junior": 1, "mid": 1, "senior": 2, "staff_plus": 1, "unspecified": 1}
    assert d["years"] == {"0-2": 1, "3-5": 2, "6-9": 1, "10+": 1, "unspecified": 1}
    assert d["travel"] == {"none": 1, "occasional": 2, "frequent": 1, "unspecified": 2}
    assert d["customer_facing"] == {"1": 1, "2": 1, "3": 1, "4": 2, "5": 1}
    assert d["verbs"][0] == ["deploy", 6] and len(d["verbs"]) <= 15


def test_segment_deltas(six):
    posts = [Posting(id=e.posting_id, title="t", company="c", url="u", full_text="x", source="s",
                     company_size_hint="startup" if e.posting_id in ("p1", "p2", "p3") else "enterprise") for e in six]
    deltas = market.segment_deltas(six, posts, freq_threshold=0.3)
    d = {x["skill"]: x for x in deltas}
    assert d["scoping"] == {"skill": "scoping", "startup": 1.0, "enterprise": 0.0}
    assert "python" not in d  # 1.0 vs 1.0, no delta


def test_gap():
    freq = {"python": {"frequency": 0.9}, "scoping": {"frequency": 0.4}, "rag": {"frequency": 0.5}, "travel_onsite": {"frequency": 0.1}}
    g = gap.gaps(freq, min_frequency=0.2)
    assert [x["canonical"] for x in g] == ["scoping"]
    assert "python" in gap.STANDARD_ROADMAP_SKILLS and "rag" in gap.STANDARD_ROADMAP_SKILLS
