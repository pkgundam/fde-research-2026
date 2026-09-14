from sources import base
from sources.base import Posting


def P(**kw):
    d = dict(id="x", title="Forward Deployed Engineer", company="Acme", url="u", full_text="t", source="s")
    d.update(kw)
    return Posting(**d)


def test_matches_title_positive():
    for t in ["Forward Deployed Engineer", "Forward-Deployed AI Engineer, Enterprise", "Senior FDE",
              "Deployment Engineer", "Solutions Engineer (AI)", "Applied AI Engineer", "Field Engineer",
              "Implementation Engineer, AI", "Forward Deployed Software Engineer - London"]:
        assert base.matches_title(t), t


def test_matches_title_negative():
    for t in ["Software Engineer", "Solutions Engineer", "Account Executive", "Field Marketing Manager",
              "Deployment Strategist Intern"]:
        assert not base.matches_title(t), t


def test_normalize_company():
    assert base.normalize_company("Scale AI, Inc.") == "scale"
    assert base.normalize_company("Harvey.com") == "harvey"
    assert base.normalize_company("Anthropic") == "anthropic"


def test_normalize_title():
    assert base.normalize_title("Senior Forward Deployed Engineer (Remote - US) [Req 123]") == "forward deployed engineer"
    assert base.normalize_title("Forward-Deployed Engineer, Staff") == "forward deployed engineer"


def test_dedupe_keeps_longest_text():
    a = P(id="a", company="Scale AI", title="Forward Deployed Engineer", full_text="short")
    b = P(id="b", company="Scale, Inc", title="Senior Forward Deployed Engineer", full_text="much longer text")
    c = P(id="c", company="Other", title="Forward Deployed Engineer")
    out = base.dedupe([a, b, c])
    assert [p.id for p in out] == ["b", "c"]


def test_size_hint_and_travel():
    assert base.size_hint("Palantir Technologies") == "enterprise"
    assert base.size_hint("Decagon") == "startup"
    assert base.size_hint("Unknown Co") == "unknown"
    assert base.travel_mentioned("Expect up to 25% travel to customer sites")
    assert not base.travel_mentioned("Fully remote role")


def test_seniority_raw():
    assert base.seniority_raw("Senior Forward Deployed Engineer") == "senior"
    assert base.seniority_raw("Staff FDE") == "staff"
    assert base.seniority_raw("Forward Deployed Engineer") == ""
