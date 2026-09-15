import json
from pathlib import Path
from aggregate import build_report_data as b
from extract import taxonomy
from sources.base import Posting

FIX_KEYS = json.loads(Path("render/fixtures/report_data.fixture.json").read_text())


def test_build_matches_fixture_shape(six):
    posts = [Posting(id=e.posting_id, title="FDE", company=f"C{i}", url="u", full_text="x", source="greenhouse",
                     posted_date=f"2026-0{i+3}-01", company_size_hint="startup" if i < 3 else "enterprise") for i, e in enumerate(six)]
    stats = [{"name": "greenhouse", "fetched": 10, "matched": 6, "kept": 6}]
    d = b.build(six, posts, stats, n_rejects=2, tx=taxonomy.load(), generated_at="2026-09-14T00:00:00Z")
    assert set(d) == set(FIX_KEYS)
    assert d["meta"]["n_postings"] == 6 and d["meta"]["n_companies"] == 6 and d["meta"]["date_range"] == ["2026-03-01", "2026-08-01"]
    assert d["meta"]["segmentation"] == {"header": 5, "inferred": 1} and d["meta"]["rejects"] == 2 and d["meta"]["adzuna_used"] is False
    assert d["meta"]["collected_on"] == "2026-09-14" and d["meta"]["recent_share"] == 1.0
    py = next(s for s in d["skills"] if s["canonical"] == "python")
    assert set(py) == set(FIX_KEYS["skills"][0]) and py["label"] == "Python" and py["cluster"] == "software_foundations"
    assert [c["key"] for c in d["clusters"]] == [c["key"] for c in FIX_KEYS["clusters"]]
    assert set(d["scatter"]) == {"median_frequency", "median_criticality", "outliers"}
    assert set(d["market"]) == set(FIX_KEYS["market"])
    assert all(set(g) == {"canonical", "label", "frequency"} for g in d["gap"])
    assert all(set(s) == {"name", "skills", "support"} for s in d["stacks"])


def test_build_uses_collect_meta_for_collected_on_and_hn_threads(six):
    posts = [Posting(id=e.posting_id, title="FDE", company=f"C{i}", url="u", full_text="x", source="greenhouse",
                     posted_date=f"2026-0{i+3}-01", company_size_hint="startup" if i < 3 else "enterprise") for i, e in enumerate(six)]
    stats = [{"name": "greenhouse", "fetched": 10, "matched": 6, "kept": 6}]
    collect_meta = {"collected_at": "2026-09-14T23:14:00+00:00", "hn_threads": {"months": 8, "first": "2026-02", "last": "2026-09"}}
    d = b.build(six, posts, stats, n_rejects=2, tx=taxonomy.load(), generated_at="2026-10-01T00:00:00Z", collect_meta=collect_meta)
    assert d["meta"]["collected_on"] == "2026-09-14"  # from collect_meta, not generated_at
    assert d["meta"]["hn_threads"] == {"months": 8, "first": "2026-02", "last": "2026-09"}


def test_build_without_collect_meta_falls_back_to_generated_at(six):
    posts = [Posting(id=e.posting_id, title="FDE", company=f"C{i}", url="u", full_text="x", source="greenhouse",
                     posted_date=f"2026-0{i+3}-01", company_size_hint="startup" if i < 3 else "enterprise") for i, e in enumerate(six)]
    stats = [{"name": "greenhouse", "fetched": 10, "matched": 6, "kept": 6}]
    d = b.build(six, posts, stats, n_rejects=2, tx=taxonomy.load(), generated_at="2026-09-14T00:00:00Z")
    assert d["meta"]["collected_on"] == "2026-09-14"
    assert d["meta"]["hn_threads"] is None


def test_run_filters_extractions_symmetrically_with_current_postings(monkeypatch, tmp_path, six):
    """I6b: an extraction whose posting_id is no longer in postings.jsonl (dropped by a later
    re-collect) must not inflate n_postings, and a posting without a current extraction must not
    appear either -> both directions filtered to their intersection."""
    monkeypatch.setattr(b, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(b, "OUT", tmp_path / "report_data.json")
    (tmp_path / "collect_stats.json").write_text(json.dumps([{"name": "greenhouse", "fetched": 2, "matched": 2, "kept": 2}]))

    # six has extractions for p1..p6; only p1 and p2 are still current postings.
    current_postings = [
        Posting(id="p1", title="FDE", company="Acme", url="u", full_text="x", source="greenhouse", posted_date="2026-06-01"),
        Posting(id="p2", title="FDE", company="Beta", url="u", full_text="x", source="greenhouse", posted_date="2026-06-01"),
    ]
    monkeypatch.setattr("extract.validate.load_valid_extractions", lambda: six)
    monkeypatch.setattr("sources.collect.load_postings", lambda: current_postings)

    out_path = b.run()
    data = json.loads(out_path.read_text())
    assert data["meta"]["n_postings"] == 2
    assert data["meta"]["n_companies"] == 2


def test_stack_name_override_and_auto_name():
    tx = taxonomy.load()
    overridden_skills = ["prototyping", "learning_agility", "consulting", "training_enablement",
                          "business_acumen", "pre_sales", "metrics_measurement"]
    assert b._stack_name(overridden_skills, tx) == "Pre-sales & field delivery"

    auto_skills = ["python", "llm_apis", "rag"]
    assert frozenset(auto_skills) not in b.STACK_NAME_OVERRIDES
    assert b._stack_name(auto_skills, tx) == " + ".join(tx.labels[c] for c in auto_skills[:3])
