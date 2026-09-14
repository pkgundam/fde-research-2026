from extract import taxonomy as T

CLUSTERS = ["software_foundations", "ai_application_engineering", "data_and_integrations",
            "deployment_and_operations", "customer_delivery", "product_thinking_and_communication"]


def test_six_clusters_in_spec_order():
    tx = T.load()
    assert list(tx.clusters.keys()) == CLUSTERS


def test_canonicals_unique_snake_case_and_aliases_unique():
    tx = T.load()
    names = [s.canonical for c in tx.clusters.values() for s in c]
    assert len(names) == len(set(names))
    assert all(n == n.lower() and " " not in n for n in names)
    seen = {}
    for c in tx.clusters.values():
        for s in c:
            for a in s.aliases:
                assert a.lower() not in seen, f"alias {a!r} in both {seen.get(a.lower())} and {s.canonical}"
                seen[a.lower()] = s.canonical


def test_generic_cloud_maps_to_generic_node_not_aws():
    tx = T.load()
    assert tx.alias_index["cloud"] == "cloud_platforms"
    assert tx.alias_index["amazon web services"] == "aws"


def test_size():
    tx = T.load()
    assert 80 <= len(tx.by_canonical) <= 110
