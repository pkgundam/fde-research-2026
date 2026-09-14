from aggregate import frequency, criticality
from extract import taxonomy


def test_skill_frequency_counts_once_per_posting(six):
    f = frequency.skill_frequency(six)
    assert f["python"] == {"n": 6, "frequency": 1.0}
    assert f["aws"] == {"n": 3, "frequency": 0.5}
    assert f["kubernetes"]["n"] == 2 and f["evals"]["n"] == 1


def test_cluster_coverage(six):
    cov = frequency.cluster_coverage(six, taxonomy.load())
    assert cov["software_foundations"] == 1.0
    assert cov["deployment_and_operations"] == 4 / 6  # aws or kubernetes: p1 p2 p3 p4
    assert cov["customer_delivery"] == 0.5
    assert cov["product_thinking_and_communication"] == 0.0


def test_skill_criticality(six):
    c = criticality.skill_criticality(six, low_n=3)
    assert c["python"]["mentions"] == {"responsibility": 2, "requirement": 6, "nice_to_have": 0}
    assert c["python"]["criticality"] == 2 / 8 and c["python"]["low_n"] is False
    assert c["scoping"]["criticality"] == 1.0
    assert c["aws"]["criticality"] == 0.0
    assert c["kubernetes"]["criticality"] == 0.5 and c["kubernetes"]["low_n"] is True
    assert c["evals"]["low_n"] is True and c["scoping"]["evidence"] == "scoping responsibility"
