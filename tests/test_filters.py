import yaml
from sources import base
from sources.base import Posting, normalize_company


def P(**kw):
    d = dict(id="x", title="Forward Deployed Engineer", company="Acme", url="u", full_text="t", source="s")
    d.update(kw)
    return Posting(**d)


# ~90-word JDs for near-duplicate dedupe tests: JD_A/JD_B are genuinely different roles (low
# shingle overlap); _BASE_JD_TEMPLATE differs only in its "Location:" line plus a trailing
# sentence, so its two fillings are near-identical (high shingle overlap).
_JD_A = (
    "We are looking for a Forward Deployed Engineer to embed with enterprise customers, "
    "build custom data pipelines, and ship production integrations that solve their most "
    "pressing operational problems. You will travel on site frequently, run workshops, "
    "debug live systems under pressure, and translate ambiguous business requirements into "
    "working software within days rather than months. Strong Python or Java skills, a "
    "customer first mindset, and comfort operating without a spec are essential. You will "
    "partner with sales engineering and product teams to unblock deals and turn pilots into "
    "long term renewals across our largest accounts."
)
_JD_B = (
    "This role sits inside our internal platform group building the tooling that keeps every "
    "downstream machine learning pipeline healthy. You will own on call rotations, design "
    "monitoring dashboards, tune Kubernetes clusters for cost and reliability, and review "
    "pull requests from a dozen teams every week. We value deep systems knowledge, an obsession "
    "with automation, and a willingness to mentor junior engineers. There is no customer travel "
    "in this position; instead you will spend your time in design reviews, incident postmortems, "
    "and quarterly planning sessions with the infrastructure leadership team."
)
_BASE_JD_TEMPLATE = (
    "We are looking for a Forward Deployed Engineer to join our customer facing team. "
    "You will work directly with enterprise customers to deploy our platform, build "
    "custom integrations, and translate customer requirements into production software. "
    "The ideal candidate has strong software engineering skills, experience with APIs and "
    "data pipelines, and enjoys working on site with customers to solve real world problems "
    "quickly. You will collaborate closely with product and engineering teams to ship "
    "features that unblock customer deployments. Location: {loc}. Some travel is required "
    "to support customer engagements and onboarding sessions throughout the year."
)


def test_matches_title_positive():
    for t in ["Forward Deployed Engineer", "Forward-Deployed AI Engineer, Enterprise", "Senior FDE",
              "Deployment Engineer", "Solutions Engineer (AI)", "Applied AI Engineer", "Field Engineer",
              "Implementation Engineer, AI", "Forward Deployed Software Engineer - London"]:
        assert base.matches_title(t), t


def test_matches_title_negative():
    for t in ["Software Engineer", "Solutions Engineer", "Account Executive", "Field Marketing Manager",
              "Deployment Strategist Intern"]:
        assert not base.matches_title(t), t


def test_matches_title_excludes_non_engineer_roles():
    for t in ["Forward Deployed Product Manager", "Engineering Manager, Forward Deployed",
              "Director, Forward Deployed Engineering", "Forward Deployed Engineer Intern"]:
        assert not base.matches_title(t), t
    for t in ["Forward Deployed Engineer", "Forward-Deployed AI Engineer, Enterprise", "Senior FDE",
              "Deployment Engineer", "Solutions Engineer (AI)", "Applied AI Engineer", "Field Engineer",
              "Implementation Engineer, AI", "Forward Deployed Software Engineer - London"]:
        assert base.matches_title(t), t


def test_normalize_company():
    assert base.normalize_company("Scale AI, Inc.") == "scale"
    assert base.normalize_company("Harvey.com") == "harvey"
    assert base.normalize_company("Anthropic") == "anthropic"


def test_normalize_title():
    assert base.normalize_title("Senior Forward Deployed Engineer (Remote - US) [Req 123]") == "forward deployed engineer"
    assert base.normalize_title("Forward-Deployed Engineer, Staff") == "forward deployed engineer"


def test_normalize_title_keeps_whole_title_when_prefix_is_not_a_match():
    assert base.normalize_title("Manager, Forward Deployed Engineering") == "manager forward deployed engineering"
    assert base.normalize_title("Software Engineer, Forward Deployed") == "software engineer forward deployed"
    assert base.normalize_title("Forward Deployed Engineer - London") == "forward deployed engineer"


def test_dedupe_keeps_longest_text():
    a = P(id="a", company="Scale AI", title="Forward Deployed Engineer", full_text="short")
    b = P(id="b", company="Scale, Inc", title="Senior Forward Deployed Engineer", full_text="much longer text")
    c = P(id="c", company="Other", title="Forward Deployed Engineer")
    out = base.dedupe([a, b, c])
    assert [p.id for p in out] == ["b", "c"]


def test_dedupe_keeps_both_when_jd_text_differs():
    """Same (company, title) key, but two genuinely different ~90-word JDs -> both kept."""
    a = P(id="a", full_text=_JD_A)
    b = P(id="b", full_text=_JD_B)
    out = base.dedupe([a, b])
    assert [p.id for p in out] == ["a", "b"]


def test_dedupe_merges_near_identical_jd_text():
    """Same (company, title) key, JDs identical except a Location line (plus one trailing
    sentence on the Berlin variant) -> near-duplicate, merged, longer text wins."""
    london = _BASE_JD_TEMPLATE.format(loc="London")
    berlin = _BASE_JD_TEMPLATE.format(loc="Berlin") + " Relocation assistance is available for the right candidate."
    a = P(id="a", full_text=london)
    b = P(id="b", full_text=berlin)
    out = base.dedupe([a, b])
    assert [p.id for p in out] == ["b"]


def test_dedupe_preserves_group_and_representative_order():
    """Groups stay in first-seen order; within a group, surviving representatives stay in the
    order they were first added, even when another group's posting is interleaved between them."""
    acme1 = P(id="acme1", company="Acme", title="Forward Deployed Engineer", full_text=_JD_A)
    other1 = P(id="other1", company="Other", title="Forward Deployed Engineer")
    acme2 = P(id="acme2", company="Acme", title="Forward Deployed Engineer", full_text=_JD_B)
    out = base.dedupe([acme1, other1, acme2])
    assert [p.id for p in out] == ["acme1", "acme2", "other1"]


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
