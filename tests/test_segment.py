from extract.segment import segment

JD = """About us
We build things.
What you'll do
- Deploy models for customers
- Scope engagements
What we're looking for
- 5+ years Python
- AWS experience
Nice to have
- Kubernetes
Benefits
- Health insurance
"""


def test_segments_by_headers():
    s = segment(JD)
    assert s.quality == "header"
    assert "Deploy models" in s.responsibilities and "Scope" in s.responsibilities
    assert "5+ years Python" in s.requirements and "AWS" in s.requirements
    assert "Kubernetes" in s.nice_to_have and "Kubernetes" not in s.requirements
    assert "Health insurance" in s.other and "We build things" in s.other


def test_alternate_headers():
    s = segment("Responsibilities:\nShip\nRequirements:\nPython\nBonus points:\nRust\n")
    assert s.responsibilities.strip() == "Ship" and s.requirements.strip() == "Python" and s.nice_to_have.strip() == "Rust"
    s = segment("The Role\nShip\nQualifications\nPython\nPreferred qualifications\nRust\n")
    assert "Ship" in s.responsibilities and "Python" in s.requirements and "Rust" in s.nice_to_have


def test_no_headers_is_inferred():
    s = segment("We want an engineer who can deploy and knows Python.")
    assert s.quality == "inferred" and s.other.strip() and not s.responsibilities


def test_good_fit_if_you_have_header_is_requirements():
    s = segment("What you'll do\nShip\nYou Might Be a Good Fit If You Have:\nPython\n")
    assert "Python" in s.requirements and "Python" not in s.responsibilities


def test_strong_candidates_may_also_have_header_is_nice_to_have():
    s = segment("What you'll do\nShip\nStrong candidates may also have:\nKubernetes\n")
    assert "Kubernetes" in s.nice_to_have and "Kubernetes" not in s.responsibilities


def test_the_ideal_candidate_will_have_header_is_requirements():
    s = segment("What you'll do\nShip\nThe ideal candidate will have\nPython\n")
    assert "Python" in s.requirements and "Python" not in s.responsibilities
