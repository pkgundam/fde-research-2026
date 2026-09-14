import pytest
from extract.schema import Extraction, SkillMention as M


def ex(pid, skills, seniority="senior", years=5, travel="occasional", cfi=4, verbs=None, quality="header"):
    return Extraction(posting_id=pid, skills=[M(canonical=c, section=s, evidence=f"{c} {s}") for c, s in skills],
                      seniority=seniority, years_required=years, travel_expectation=travel, customer_facing_intensity=cfi,
                      responsibility_verbs=verbs or ["build", "deploy", "scope", "own", "present"], segmentation_quality=quality)


@pytest.fixture
def six():
    """6 postings. python in 6 (1 responsibility, 5 requirement); aws in 3 (all requirement);
    scoping in 3 (3 responsibility); kubernetes in 2 (1 resp, 1 nice); evals in 1 (resp)."""
    return [
        ex("p1", [("python", "requirement"), ("aws", "requirement"), ("scoping", "responsibility"), ("kubernetes", "responsibility")], seniority="senior", years=5, travel="frequent", cfi=5),
        ex("p2", [("python", "requirement"), ("python", "responsibility"), ("aws", "requirement"), ("scoping", "responsibility")], seniority="mid", years=3, travel="occasional", cfi=4),
        ex("p3", [("python", "requirement"), ("aws", "requirement"), ("scoping", "responsibility"), ("evals", "responsibility")], seniority="senior", years=6, travel="none", cfi=3),
        ex("p4", [("python", "requirement"), ("kubernetes", "nice_to_have")], seniority="staff_plus", years=10, travel="unspecified", cfi=2, quality="inferred"),
        ex("p5", [("python", "requirement")], seniority="unspecified", years=None, travel="unspecified", cfi=1, verbs=["ship", "deploy", "scope", "own", "present"]),
        ex("p6", [("python", "requirement"), ("python", "responsibility")], seniority="junior", years=1, travel="occasional", cfi=4),
    ]
