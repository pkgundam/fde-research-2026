import yaml
from sources import base
from sources.base import Posting, normalize_company


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


def test_size_map_consistency():
    """Verify SIZE_MAP entries match normalized candidate names and vice versa."""
    with open("sources/companies.yaml") as f:
        data = yaml.safe_load(f)

    candidates = data["candidates"]
    candidate_norms = {normalize_company(c["name"]): c["name"] for c in candidates}

    # Test 1: every candidate should have a valid size_hint
    valid_hints = {"startup", "scaleup", "enterprise", "unknown"}
    for c in candidates:
        name = c["name"]
        hint = base.size_hint(name)
        assert hint in valid_hints, f"size_hint({name!r}) returned {hint!r}, not in {valid_hints}"

    # Test 2: every SIZE_MAP entry must be a normalized candidate name
    all_size_map_entries = set()
    for hint, names in base.SIZE_MAP.items():
        for name in names:
            all_size_map_entries.add(name)
            assert name in candidate_norms, f"SIZE_MAP entry {name!r} ({hint}) is not a normalized candidate name"

    # Test 3: no SIZE_MAP entry should be duplicated across categories
    all_entries_list = []
    for names in base.SIZE_MAP.values():
        all_entries_list.extend(names)
    assert len(all_entries_list) == len(all_size_map_entries), "SIZE_MAP has duplicate entries across categories"
