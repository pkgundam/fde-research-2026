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


def test_spearman_perfect_and_reversed_and_tied():
    assert criticality.spearman([1, 2, 3, 4, 5], [10, 20, 30, 40, 50]) == 1.0
    assert criticality.spearman([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) == -1.0
    # a known tied case: x has a tie at rank (2,3); Pearson on tie-averaged ranks gives 0.9487
    assert round(criticality.spearman([1, 2, 2, 4], [1, 2, 3, 4]), 4) == round(0.9486832980505138, 4)
